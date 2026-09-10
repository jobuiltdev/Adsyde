import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finishing', '0001_initial'),
        ('generations', '0002_provider_readiness'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RegenerationRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_key', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('generation', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='regenerated_from_request', to='generations.generation')),
                ('source_generation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='regeneration_requests', to='generations.generation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('user', 'source_generation', 'request_key'), name='regeneration_request_unique')],
            },
        ),
    ]
