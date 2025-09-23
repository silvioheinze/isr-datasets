# Generated manually to remove keywords field only

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0021_update_model_state'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='keywords',
        ),
    ]
