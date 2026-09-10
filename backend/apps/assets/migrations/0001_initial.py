import apps.assets.models
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('category', models.CharField(choices=[('product_image', 'Product image'), ('logo', 'Logo'), ('reference_image', 'Reference image')], max_length=32)),
                ('file', models.FileField(max_length=500, upload_to=apps.assets.models.asset_upload_to)),
                ('original_filename', models.CharField(max_length=255)),
                ('mime_type', models.CharField(max_length=32)),
                ('size', models.PositiveBigIntegerField()),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='projects.project')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
                'constraints': [models.CheckConstraint(condition=models.Q(('size__gt', 0)), name='asset_size_positive'), models.CheckConstraint(condition=models.Q(('width__gt', 0)), name='asset_width_positive'), models.CheckConstraint(condition=models.Q(('height__gt', 0)), name='asset_height_positive'), models.CheckConstraint(condition=models.Q(('category__in', ['product_image', 'logo', 'reference_image'])), name='asset_category_valid')],
            },
        ),
    ]
