# Generated manually to update ImportQueue ordering

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0023_add_import_queue'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='importqueue',
            options={'ordering': ['created_at'], 'verbose_name': 'Import Queue Entry', 'verbose_name_plural': 'Import Queue Entries'},
        ),
    ]

