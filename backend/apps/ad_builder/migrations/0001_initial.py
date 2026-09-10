import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('assets', '0001_initial'),
        ('generations', '0002_provider_readiness'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('business_product', models.CharField(max_length=1000)),
                ('offer_objective', models.CharField(blank=True, max_length=1000)),
                ('audience', models.CharField(blank=True, max_length=500)),
                ('style', models.CharField(default='premium', max_length=32)),
                ('style_notes', models.CharField(blank=True, max_length=500)),
                ('platform', models.CharField(choices=[('tiktok', 'TikTok'), ('instagram_reels', 'Instagram Reels'), ('instagram_feed', 'Instagram Feed'), ('youtube_shorts', 'YouTube Shorts'), ('youtube', 'YouTube'), ('general_social', 'General social')], default='instagram_reels', max_length=32)),
                ('call_to_action', models.CharField(blank=True, max_length=200)),
                ('selling_points', models.JSONField(default=list)),
                ('model', models.CharField(default='mock-standard', max_length=64)),
                ('aspect_ratio', models.CharField(default='9:16', max_length=8)),
                ('duration_seconds', models.PositiveSmallIntegerField(default=10)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('planned', 'Planned'), ('generated', 'Generated'), ('archived', 'Archived')], default='draft', max_length=16)),
                ('planner_version', models.CharField(default='deterministic-v1', max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ad_plans', to='projects.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ad_plans', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_at', '-id'),
            },
        ),
        migrations.CreateModel(
            name='AdPlanAsset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('asset_id_snapshot', models.UUIDField()),
                ('filename_snapshot', models.CharField(max_length=255)),
                ('category_snapshot', models.CharField(max_length=32)),
                ('mime_type_snapshot', models.CharField(max_length=32)),
                ('role', models.CharField(choices=[('primary_product', 'Primary product'), ('additional_product', 'Additional product'), ('logo', 'Logo'), ('visual_reference', 'Visual reference')], max_length=32)),
                ('position', models.PositiveSmallIntegerField()),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.asset')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='selected_assets', to='ad_builder.adplan')),
            ],
            options={
                'ordering': ('position', 'id'),
            },
        ),
        migrations.CreateModel(
            name='AdPlanRevision',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('number', models.PositiveSmallIntegerField()),
                ('request_key', models.CharField(max_length=128)),
                ('variant', models.CharField(max_length=32)),
                ('template_version', models.CharField(default='prompt-template-v1', max_length=32)),
                ('concept', models.TextField()),
                ('hook', models.TextField()),
                ('script_sections', models.JSONField(default=list)),
                ('shots', models.JSONField(default=list)),
                ('planner_prompt', models.TextField()),
                ('reviewed_concept', models.TextField()),
                ('reviewed_hook', models.TextField()),
                ('reviewed_script_sections', models.JSONField(default=list)),
                ('reviewed_shots', models.JSONField(default=list)),
                ('reviewed_prompt', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('generation', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_plan_revision', to='generations.generation')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='ad_builder.adplan')),
            ],
            options={
                'ordering': ('-number',),
            },
        ),
        migrations.CreateModel(
            name='GenerationReference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_id_snapshot', models.UUIDField()),
                ('filename_snapshot', models.CharField(max_length=255)),
                ('category_snapshot', models.CharField(max_length=32)),
                ('role', models.CharField(choices=[('primary_product', 'Primary product'), ('additional_product', 'Additional product'), ('logo', 'Logo'), ('visual_reference', 'Visual reference')], max_length=32)),
                ('position', models.PositiveSmallIntegerField()),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.asset')),
                ('generation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='references', to='generations.generation')),
            ],
            options={
                'ordering': ('position',),
            },
        ),
        migrations.AddIndex(
            model_name='adplan',
            index=models.Index(fields=['project', '-updated_at'], name='plan_project_time_idx'),
        ),
        migrations.AddConstraint(
            model_name='adplanasset',
            constraint=models.UniqueConstraint(fields=('plan', 'position'), name='plan_asset_position_unique'),
        ),
        migrations.AddConstraint(
            model_name='adplanasset',
            constraint=models.UniqueConstraint(fields=('plan', 'asset_id_snapshot'), name='plan_asset_unique'),
        ),
        migrations.AddConstraint(
            model_name='adplanrevision',
            constraint=models.UniqueConstraint(fields=('plan', 'number'), name='plan_revision_number_unique'),
        ),
        migrations.AddConstraint(
            model_name='adplanrevision',
            constraint=models.UniqueConstraint(fields=('plan', 'request_key'), name='plan_revision_request_unique'),
        ),
        migrations.AddConstraint(
            model_name='generationreference',
            constraint=models.UniqueConstraint(fields=('generation', 'position'), name='generation_reference_position_unique'),
        ),
    ]
