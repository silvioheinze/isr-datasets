# Generated manually to update Django model state to match database

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0020_finalize_uuid_primary_key'),
    ]

    operations = [
        # This migration is just to update Django's model state
        # The database is already in the correct state from previous migrations
        migrations.AlterField(
            model_name='dataset',
            name='id',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                help_text='Unique identifier for the dataset',
                primary_key=True,
                serialize=False,
                verbose_name='ID'
            ),
        ),
    ]
