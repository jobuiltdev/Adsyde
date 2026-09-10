from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.ad_builder.models import AdPlan, AdPlanRevision, GenerationReference, PlanStatus
from apps.ad_builder.planner import DeterministicPlanner, PlannerRequest
from apps.assets.models import Asset
from apps.credits.models import GenerationCharge
from apps.credits.services import grant_credits
from apps.projects.models import Project


def make_user(email):
    account = User.objects.create_user(email, "valid-test-password-72!")
    account.email_verified_at = timezone.now()
    account.save(update_fields=["email_verified_at"])
    return account


def auth_client(account):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(account).access_token}")
    return client


def make_asset(project, name="product.png"):
    return Asset.objects.create(
        project=project,
        category="product_image",
        file=SimpleUploadedFile(name, b"image"),
        original_filename=name,
        mime_type="image/png",
        size=5,
        width=1,
        height=1,
    )


def plan_payload(asset=None):
    payload = {
        "business_product": "Handmade candles",
        "offer_objective": "Introduce the collection",
        "audience": "People furnishing a new home",
        "style": "warm",
        "style_notes": "Natural evening light",
        "platform": "instagram_reels",
        "call_to_action": "Send us a message",
        "selling_points": ["Made locally", "Reusable jars"],
        "model": "mock-standard",
        "aspect_ratio": "9:16",
        "duration_seconds": 10,
    }
    if asset:
        payload["selected_asset_inputs"] = [
            {"asset_id": str(asset.pk), "role": "primary_product", "position": 0}
        ]
    return payload


def planner_request(category="Home cleaning", platform="instagram_reels", revision=1):
    return PlannerRequest(
        business_product=category,
        offer_objective="Book this week",
        audience="Busy households",
        style="Professional",
        style_notes="Bright and clear",
        platform=platform,
        call_to_action="Book today",
        selling_points=("Flexible appointments",),
        duration_seconds=10,
        aspect_ratio="9:16",
        brand_name="Clear Home",
        brand_context="Reliable",
        asset_labels=("service.png",),
        revision_number=revision,
    )


@pytest.mark.parametrize(
    "category",
    ["Fashion", "Restaurant", "Beauty", "Barber", "Home services", "Real estate", "E-commerce"],
)
def test_planner_is_business_neutral_and_duration_coherent(category):
    result = DeterministicPlanner().plan(planner_request(category))
    assert category in result.concept
    assert sum(shot["duration_ms"] for shot in result.shots) == 10_000
    assert [shot["start_ms"] for shot in result.shots] == [0, 3334, 6667]
    assert result.generation_prompt.startswith("Create a 10-second 9:16 social video ad")


def test_planner_is_stable_platform_aware_and_revision_varied():
    planner = DeterministicPlanner()
    first = planner.plan(planner_request(platform="youtube"))
    repeat = planner.plan(planner_request(platform="youtube"))
    second = planner.plan(planner_request(platform="youtube", revision=2))
    assert first == repeat
    assert first.variant != second.variant
    assert "confident narrative pacing" in first.generation_prompt
    assert first.hook != second.hook


@pytest.mark.django_db
def test_plan_crud_persists_draft_and_asset_snapshot(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Launch")
    asset = make_asset(project)
    client = auth_client(owner)
    created = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/", plan_payload(asset), format="json"
    )
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "draft"
    assert data["selected_assets"][0]["filename"] == "product.png"
    resumed = client.get(f"/api/v1/projects/{project.pk}/ad-plans/{data['id']}/")
    assert resumed.status_code == 200
    assert resumed.json()["business_product"] == "Handmade candles"
    asset.delete()
    assert AdPlan.objects.get().selected_assets.get().asset is None
    assert AdPlan.objects.get().selected_assets.get().filename_snapshot == "product.png"


@pytest.mark.django_db
def test_foreign_assets_and_plan_access_are_rejected():
    owner = make_user("owner@example.com")
    stranger = make_user("stranger@example.com")
    project = Project.objects.create(owner=owner, name="Owner")
    foreign_project = Project.objects.create(owner=stranger, name="Private")
    foreign_asset = make_asset(foreign_project)
    client = auth_client(owner)
    rejected = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/", plan_payload(foreign_asset), format="json"
    )
    assert rejected.status_code == 400
    plan = AdPlan.objects.create(user=stranger, project=foreign_project, **plan_payload())
    assert (
        client.get(f"/api/v1/projects/{foreign_project.pk}/ad-plans/{plan.pk}/").status_code == 404
    )
    assert (
        client.patch(
            f"/api/v1/projects/{foreign_project.pk}/ad-plans/{plan.pk}/", {}, format="json"
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_planning_is_idempotent_and_preserves_revisions():
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Launch", business_name="Glow")
    client = auth_client(owner)
    plan = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/", plan_payload(), format="json"
    ).json()
    url = f"/api/v1/projects/{project.pk}/ad-plans/{plan['id']}/plan/"
    first = client.post(url, HTTP_IDEMPOTENCY_KEY="request-one")
    repeat = client.post(url, HTTP_IDEMPOTENCY_KEY="request-one")
    second = client.post(url, HTTP_IDEMPOTENCY_KEY="request-two")
    assert first.status_code == repeat.status_code == second.status_code == 201
    assert first.json()["id"] == repeat.json()["id"]
    assert first.json()["id"] != second.json()["id"]
    assert AdPlanRevision.objects.filter(plan_id=plan["id"]).count() == 2


@pytest.mark.django_db
def test_reviewed_content_is_persisted_and_direct_generation_is_exact(settings):
    settings.CREDIT_DEVELOPMENT_INITIAL_GRANT = 0
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Launch")
    asset = make_asset(project)
    grant_credits(owner, 500, "Test", "test:fund-builder")
    client = auth_client(owner)
    plan = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/", plan_payload(asset), format="json"
    ).json()
    revision = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/{plan['id']}/plan/",
        HTTP_IDEMPOTENCY_KEY="request-one",
    ).json()
    revision_url = (
        f"/api/v1/projects/{project.pk}/ad-plans/{plan['id']}/revisions/{revision['id']}/"
    )
    reviewed_prompt = "Use this exact reviewed prompt without additions."
    edited = client.patch(
        revision_url,
        {"reviewed_hook": "Edited hook", "reviewed_prompt": reviewed_prompt},
        format="json",
    )
    assert edited.status_code == 200
    with patch("apps.generations.tasks.submit_generation_task.delay"):
        generated = client.post(f"{revision_url}generate/")
    assert generated.status_code == 201
    generation_id = generated.json()["id"]
    revision_row = AdPlanRevision.objects.get(pk=revision["id"])
    assert revision_row.reviewed_hook == "Edited hook"
    assert revision_row.generation.prompt == reviewed_prompt
    assert (
        GenerationReference.objects.get(generation_id=generation_id).filename_snapshot
        == "product.png"
    )
    assert GenerationCharge.objects.filter(generation_id_snapshot=generation_id).count() == 1
    with patch("apps.generations.tasks.submit_generation_task.delay"):
        assert client.post(f"{revision_url}generate/").json()["id"] == generation_id
    assert GenerationCharge.objects.filter(generation_id_snapshot=generation_id).count() == 1


@pytest.mark.django_db
def test_insufficient_credits_block_only_generation(settings):
    settings.CREDIT_DEVELOPMENT_INITIAL_GRANT = 0
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Launch")
    client = auth_client(owner)
    plan = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/", plan_payload(), format="json"
    ).json()
    revision = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/{plan['id']}/plan/",
        HTTP_IDEMPOTENCY_KEY="request-one",
    )
    assert revision.status_code == 201
    generated = client.post(
        f"/api/v1/projects/{project.pk}/ad-plans/{plan['id']}/revisions/{revision.json()['id']}/generate/"
    )
    assert generated.status_code == 409
    assert AdPlanRevision.objects.get(pk=revision.json()["id"]).generation is None


@pytest.mark.django_db
def test_deletion_policy_preserves_generated_history():
    owner = make_user("owner@example.com")
    project = Project.objects.create(owner=owner, name="Launch")
    client = auth_client(owner)
    draft = AdPlan.objects.create(user=owner, project=project, **plan_payload())
    assert client.delete(f"/api/v1/projects/{project.pk}/ad-plans/{draft.pk}/").status_code == 204
    assert not AdPlan.objects.filter(pk=draft.pk).exists()
    generated = AdPlan.objects.create(
        user=owner, project=project, status=PlanStatus.GENERATED, **plan_payload()
    )
    from apps.generations.models import Generation

    generation = Generation.objects.create(
        project=project,
        created_by=owner,
        prompt="Exact",
        model="mock-standard",
        aspect_ratio="9:16",
        duration_seconds=10,
    )
    AdPlanRevision.objects.create(
        plan=generated,
        number=1,
        request_key="request-one",
        variant="direct_benefit",
        concept="Concept",
        hook="Hook",
        script_sections=[],
        shots=[],
        planner_prompt="Prompt",
        reviewed_concept="Concept",
        reviewed_hook="Hook",
        reviewed_script_sections=[],
        reviewed_shots=[],
        reviewed_prompt="Exact",
        generation=generation,
    )
    assert (
        client.delete(f"/api/v1/projects/{project.pk}/ad-plans/{generated.pk}/").status_code == 204
    )
    generated.refresh_from_db()
    assert generated.status == PlanStatus.ARCHIVED
    assert client.delete(f"/api/v1/projects/{project.pk}/").status_code == 400
    assert Project.objects.filter(pk=project.pk).exists()
