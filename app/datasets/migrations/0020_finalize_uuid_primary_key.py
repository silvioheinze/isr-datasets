# Generated manually to finalize UUID primary key conversion

from django.db import migrations


def finalize_uuid_primary_key(apps, schema_editor):
    """Finalize the UUID primary key change using raw SQL"""
    if schema_editor.connection.vendor == 'postgresql':
        # Now that ManyToMany relationships are handled, we can safely drop the primary key
        
        # Drop the primary key constraint on the old id field
        schema_editor.execute("ALTER TABLE datasets_dataset DROP CONSTRAINT datasets_dataset_pkey;")
        
        # Make uuid field NOT NULL
        schema_editor.execute("ALTER TABLE datasets_dataset ALTER COLUMN uuid SET NOT NULL;")
        
        # Add primary key constraint to uuid field
        schema_editor.execute("ALTER TABLE datasets_dataset ADD CONSTRAINT datasets_dataset_pkey PRIMARY KEY (uuid);")
        
        # Drop the old id column
        schema_editor.execute("ALTER TABLE datasets_dataset DROP COLUMN id;")
        
        # Rename uuid column to id
        schema_editor.execute("ALTER TABLE datasets_dataset RENAME COLUMN uuid TO id;")


def reverse_finalize_uuid_primary_key(apps, schema_editor):
    """Reverse operation - this is complex and may not be fully reversible"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0019_handle_manytomany_for_uuid'),
    ]

    operations = [
        migrations.RunPython(
            finalize_uuid_primary_key,
            reverse_finalize_uuid_primary_key,
        ),
    ]
