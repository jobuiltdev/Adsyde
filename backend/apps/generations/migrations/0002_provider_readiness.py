from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("generations", "0001_initial")]

    operations = [
        migrations.AddField(model_name="generation", name="provider_accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="generation", name="unknown_since", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="generation", name="last_reconciled_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="generation", name="cancel_requested_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="generation", name="cancel_confirmed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="generation", name="result_ingested_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="providerevent", name="provider_job_id", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="providerevent", name="processed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="providerevent", name="processing_outcome", field=models.CharField(blank=True, max_length=32)),
        migrations.AddIndex(model_name="generation", index=models.Index(fields=["provider_key", "provider_job_id"], name="gen_provider_job_idx")),
        migrations.AddIndex(model_name="generation", index=models.Index(fields=["status"], name="gen_status_idx")),
        migrations.AddIndex(model_name="generation", index=models.Index(fields=["project", "-created_at"], name="gen_project_created_idx")),
    ]
