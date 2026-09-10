import apps.finishing.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ad_builder', '0001_initial'),
        ('assets', '0001_initial'),
        ('generations', '0002_provider_readiness'),
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdFinish',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('rendering', 'Rendering'), ('completed', 'Completed'), ('failed', 'Failed'), ('archived', 'Archived')], default='draft', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='finishes', to='projects.project')),
                ('source_generation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='finishes', to='generations.generation')),
                ('source_plan_revision', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ad_builder.adplanrevision')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-updated_at', '-id'),
            },
        ),
        migrations.CreateModel(
            name='FinishRevision',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('number', models.PositiveSmallIntegerField()),
                ('request_key', models.CharField(max_length=128)),
                ('captions_enabled', models.BooleanField(default=True)),
                ('caption_source', models.CharField(default='manual', max_length=16)),
                ('caption_language', models.CharField(default='en', max_length=12)),
                ('caption_style', models.CharField(default='clean', max_length=16)),
                ('caption_position', models.CharField(default='bottom', max_length=16)),
                ('caption_segments', models.JSONField(default=list)),
                ('voiceover_enabled', models.BooleanField(default=False)),
                ('voice_script', models.TextField(blank=True)),
                ('voice_key', models.CharField(default='neutral', max_length=16)),
                ('voice_speed_percent', models.PositiveSmallIntegerField(default=100)),
                ('music_enabled', models.BooleanField(default=False)),
                ('music_key', models.CharField(default='none', max_length=16)),
                ('music_volume_percent', models.PositiveSmallIntegerField(default=20)),
                ('fade_in_ms', models.PositiveIntegerField(default=300)),
                ('fade_out_ms', models.PositiveIntegerField(default=300)),
                ('watermark_enabled', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('finish', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revisions', to='finishing.adfinish')),
                ('thumbnail_asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='assets.asset')),
            ],
            options={
                'ordering': ('-number',),
            },
        ),
        migrations.CreateModel(
            name='RenderedAd',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(max_length=500, upload_to=apps.finishing.models.rendered_output_path)),
                ('mime_type', models.CharField(max_length=32)),
                ('size_bytes', models.PositiveBigIntegerField()),
                ('duration_ms', models.PositiveIntegerField()),
                ('aspect_ratio', models.CharField(max_length=8)),
                ('render_version', models.CharField(default='local-copy-v1', max_length=32)),
                ('captions_applied', models.BooleanField(default=False)),
                ('voiceover_applied', models.BooleanField(default=False)),
                ('music_applied', models.BooleanField(default=False)),
                ('watermark_applied', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('revision', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='output', to='finishing.finishrevision')),
            ],
        ),
        migrations.AddIndex(
            model_name='adfinish',
            index=models.Index(fields=['project', '-updated_at'], name='finish_project_time_idx'),
        ),
        migrations.AddConstraint(
            model_name='finishrevision',
            constraint=models.UniqueConstraint(fields=('finish', 'number'), name='finish_revision_number_unique'),
        ),
        migrations.AddConstraint(
            model_name='finishrevision',
            constraint=models.UniqueConstraint(fields=('finish', 'request_key'), name='finish_revision_request_unique'),
        ),
    ]
