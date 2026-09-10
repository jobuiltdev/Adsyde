from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.assets.models import Asset
from apps.credits.exceptions import InvalidPricingOption
from apps.credits.pricing import PricingUnavailable
from apps.credits.services import reserve_generation
from apps.generations.models import Generation, GenerationStatus
from apps.generations.services import ACTIVE_STATUSES
from apps.providers.registry import get_active_provider

from .models import AdPlanAsset, AdPlanRevision, GenerationReference, PlanStatus
from .planner import DeterministicPlanner, PlannerRequest


def sync_assets(plan, selections):
    if len(selections) > 8:
        raise ValidationError({"selected_assets": ["Select no more than 8 assets."]})
    ids = [item["asset_id"] for item in selections]
    assets = {asset.pk: asset for asset in Asset.objects.filter(pk__in=ids, project=plan.project)}
    if len(assets) != len(set(ids)):
        raise ValidationError({"selected_assets": ["Every asset must belong to this project."]})
    if len({item["position"] for item in selections}) != len(selections):
        raise ValidationError({"selected_assets": ["Asset positions must be unique."]})
    plan.selected_assets.all().delete()
    AdPlanAsset.objects.bulk_create(
        [
            AdPlanAsset(
                plan=plan,
                asset=assets[item["asset_id"]],
                asset_id_snapshot=item["asset_id"],
                filename_snapshot=assets[item["asset_id"]].original_filename,
                category_snapshot=assets[item["asset_id"]].category,
                mime_type_snapshot=assets[item["asset_id"]].mime_type,
                role=item["role"],
                position=item["position"],
            )
            for item in selections
        ]
    )


@transaction.atomic
def create_revision(plan, request_key):
    existing = AdPlanRevision.objects.filter(plan=plan, request_key=request_key).first()
    if existing:
        return existing
    plan = type(plan).objects.select_for_update().select_related("project").get(pk=plan.pk)
    number = plan.revisions.count() + 1
    assets = tuple(item.filename_snapshot for item in plan.selected_assets.all())
    result = DeterministicPlanner().plan(
        PlannerRequest(
            business_product=plan.business_product,
            offer_objective=plan.offer_objective,
            audience=plan.audience,
            style=plan.style,
            style_notes=plan.style_notes,
            platform=plan.platform,
            call_to_action=plan.call_to_action,
            selling_points=tuple(plan.selling_points),
            duration_seconds=plan.duration_seconds,
            aspect_ratio=plan.aspect_ratio,
            brand_name=plan.project.business_name,
            brand_context=plan.project.brand_style,
            asset_labels=assets,
            revision_number=number,
        )
    )
    revision = AdPlanRevision.objects.create(
        plan=plan,
        number=number,
        request_key=request_key,
        variant=result.variant,
        concept=result.concept,
        hook=result.hook,
        script_sections=result.script_sections,
        shots=result.shots,
        planner_prompt=result.generation_prompt,
        reviewed_concept=result.concept,
        reviewed_hook=result.hook,
        reviewed_script_sections=result.script_sections,
        reviewed_shots=result.shots,
        reviewed_prompt=result.generation_prompt,
    )
    plan.status = PlanStatus.PLANNED
    plan.save(update_fields=["status", "updated_at"])
    return revision


@transaction.atomic
def generate_from_revision(revision, user):
    revision = (
        AdPlanRevision.objects.select_for_update()
        .select_related("plan", "plan__project")
        .get(pk=revision.pk)
    )
    if revision.generation_id:
        return revision.generation
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if Generation.objects.filter(created_by=user, status__in=ACTIVE_STATUSES).count() >= (
        settings.GENERATION_MAX_ACTIVE_PER_USER
    ):
        raise ValidationError({"generation": ["The active generation limit has been reached."]})
    generation = Generation.objects.create(
        project=revision.plan.project,
        created_by=user,
        prompt=revision.reviewed_prompt,
        provider_key=get_active_provider().key,
        model=revision.plan.model,
        aspect_ratio=revision.plan.aspect_ratio,
        duration_seconds=revision.plan.duration_seconds,
        status=GenerationStatus.QUEUED,
    )
    try:
        reserve_generation(generation)
    except PricingUnavailable as exc:
        raise InvalidPricingOption from exc
    GenerationReference.objects.bulk_create(
        [
            GenerationReference(
                generation=generation,
                asset=item.asset,
                asset_id_snapshot=item.asset_id_snapshot,
                filename_snapshot=item.filename_snapshot,
                category_snapshot=item.category_snapshot,
                role=item.role,
                position=item.position,
            )
            for item in revision.plan.selected_assets.all()
        ]
    )
    revision.generation = generation
    revision.save(update_fields=["generation", "updated_at"])
    revision.plan.status = PlanStatus.GENERATED
    revision.plan.save(update_fields=["status", "updated_at"])
    from apps.generations.tasks import submit_generation_task

    transaction.on_commit(lambda: submit_generation_task.delay(str(generation.pk)))
    return generation
