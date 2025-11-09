from django.db import migrations, models
import datasets.models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0022_remove_keywords_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetVersionFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=datasets.models.dataset_version_attachment_upload_path)),
                ('file_size', models.BigIntegerField(default=0)),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('version', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='files', to='datasets.datasetversion')),
            ],
            options={
                'ordering': ['uploaded_at', 'id'],
            },
        ),
    ]

