# Generated manually to handle ManyToMany relationships for UUID migration

from django.db import migrations


def handle_manytomany_for_uuid(apps, schema_editor):
    """Handle ManyToMany relationships for UUID migration"""
    if schema_editor.connection.vendor == 'postgresql':
        # First, we need to create new intermediate tables with UUID foreign keys
        # and populate them with data from the old tables
        
        # 1. Handle contributors ManyToMany
        schema_editor.execute("""
            CREATE TABLE datasets_dataset_contributors_new (
                id SERIAL PRIMARY KEY,
                dataset_id UUID NOT NULL,
                customuser_id INTEGER NOT NULL,
                FOREIGN KEY (dataset_id) REFERENCES datasets_dataset(uuid) ON DELETE CASCADE,
                FOREIGN KEY (customuser_id) REFERENCES user_customuser(id) ON DELETE CASCADE,
                UNIQUE(dataset_id, customuser_id)
            );
        """)
        
        # Copy data from old table to new table
        schema_editor.execute("""
            INSERT INTO datasets_dataset_contributors_new (dataset_id, customuser_id)
            SELECT d.uuid, dc.customuser_id
            FROM datasets_dataset_contributors dc
            JOIN datasets_dataset d ON dc.dataset_id = d.id;
        """)
        
        # 2. Handle related_datasets ManyToMany
        schema_editor.execute("""
            CREATE TABLE datasets_dataset_related_datasets_new (
                id SERIAL PRIMARY KEY,
                from_dataset_id UUID NOT NULL,
                to_dataset_id UUID NOT NULL,
                FOREIGN KEY (from_dataset_id) REFERENCES datasets_dataset(uuid) ON DELETE CASCADE,
                FOREIGN KEY (to_dataset_id) REFERENCES datasets_dataset(uuid) ON DELETE CASCADE,
                UNIQUE(from_dataset_id, to_dataset_id)
            );
        """)
        
        # Copy data from old table to new table
        schema_editor.execute("""
            INSERT INTO datasets_dataset_related_datasets_new (from_dataset_id, to_dataset_id)
            SELECT d1.uuid, d2.uuid
            FROM datasets_dataset_related_datasets drd
            JOIN datasets_dataset d1 ON drd.from_dataset_id = d1.id
            JOIN datasets_dataset d2 ON drd.to_dataset_id = d2.id;
        """)
        
        # 3. Handle projects ManyToMany
        schema_editor.execute("""
            CREATE TABLE datasets_dataset_projects_new (
                id SERIAL PRIMARY KEY,
                dataset_id UUID NOT NULL,
                project_id INTEGER NOT NULL,
                FOREIGN KEY (dataset_id) REFERENCES datasets_dataset(uuid) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects_project(id) ON DELETE CASCADE,
                UNIQUE(dataset_id, project_id)
            );
        """)
        
        # Copy data from old table to new table
        schema_editor.execute("""
            INSERT INTO datasets_dataset_projects_new (dataset_id, project_id)
            SELECT d.uuid, dp.project_id
            FROM datasets_dataset_projects dp
            JOIN datasets_dataset d ON dp.dataset_id = d.id;
        """)
        
        # Drop old intermediate tables
        schema_editor.execute("DROP TABLE datasets_dataset_contributors CASCADE;")
        schema_editor.execute("DROP TABLE datasets_dataset_related_datasets CASCADE;")
        schema_editor.execute("DROP TABLE datasets_dataset_projects CASCADE;")
        
        # Rename new tables to original names
        schema_editor.execute("ALTER TABLE datasets_dataset_contributors_new RENAME TO datasets_dataset_contributors;")
        schema_editor.execute("ALTER TABLE datasets_dataset_related_datasets_new RENAME TO datasets_dataset_related_datasets;")
        schema_editor.execute("ALTER TABLE datasets_dataset_projects_new RENAME TO datasets_dataset_projects;")


def reverse_handle_manytomany_for_uuid(apps, schema_editor):
    """Reverse operation - this is complex and may not be fully reversible"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0018_update_foreign_keys_to_uuid'),
    ]

    operations = [
        migrations.RunPython(
            handle_manytomany_for_uuid,
            reverse_handle_manytomany_for_uuid,
        ),
    ]
