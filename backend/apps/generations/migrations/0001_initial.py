import apps.generations.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Generation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('prompt', models.TextField()),
                ('provider_key', models.CharField(default='mock', editable=False, max_length=32)),
                ('provider_job_id', models.CharField(blank=True, max_length=255)),
                ('idempotency_key', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('model', models.CharField(max_length=64)),
                ('aspect_ratio', models.CharField(choices=[('9:16', '9:16'), ('1:1', '1:1'), ('16:9', '16:9')], max_length=8)),
                ('duration_seconds', models.PositiveSmallIntegerField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('queued', 'Queued'), ('submitted', 'Submitted'), ('processing', 'Processing'), ('unknown', 'Awaiting reconciliation'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='draft', max_length=16)),
                ('result_file', models.FileField(blank=True, max_length=500, upload_to=apps.generations.models.generation_result_path)),
                ('result_mime_type', models.CharField(blank=True, max_length=32)),
                ('error_code', models.CharField(blank=True, max_length=64)),
                ('error_detail', models.CharField(blank=True, max_length=255)),
                ('submission_attempts', models.PositiveSmallIntegerField(default=0)),
                ('poll_attempts', models.PositiveSmallIntegerField(default=0)),
                ('reconciliation_attempts', models.PositiveSmallIntegerField(default=0)),
                ('mock_scenario', models.CharField(default='success', editable=False, max_length=32)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='generations', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='generations', to='projects.project')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='ProviderEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('provider_key', models.CharField(max_length=32)),
                ('event_id', models.CharField(max_length=255)),
                ('event_type', models.CharField(max_length=32)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('generation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='generations.generation')),
            ],
        ),
        migrations.AddConstraint(
            model_name='generation',
            constraint=models.CheckConstraint(condition=models.Q(('prompt', ''), _negated=True), name='generation_prompt_not_empty'),
        ),
        migrations.AddConstraint(
            model_name='generation',
            constraint=models.CheckConstraint(condition=models.Q(('aspect_ratio__in', ['9:16', '1:1', '16:9'])), name='generation_aspect_valid'),
        ),
        migrations.AddConstraint(
            model_name='generation',
            constraint=models.CheckConstraint(condition=models.Q(('duration_seconds__gt', 0)), name='generation_duration_positive'),
        ),
        migrations.AddConstraint(
            model_name='generation',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['draft', 'queued', 'submitted', 'processing', 'unknown', 'completed', 'failed', 'cancelled'])), name='generation_status_valid'),
        ),
        migrations.AddConstraint(
            model_name='providerevent',
            constraint=models.UniqueConstraint(fields=('provider_key', 'event_id'), name='provider_event_unique'),
        ),
    ]
