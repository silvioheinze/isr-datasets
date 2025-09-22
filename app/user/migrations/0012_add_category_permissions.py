# Generated manually to add category permissions to Administrator role

from django.db import migrations


def add_category_permissions(apps, schema_editor):
    """Add category management permissions to Administrator role"""
    Role = apps.get_model('user', 'Role')
    
    try:
        admin_role = Role.objects.get(name='Administrator')
        
        # Get current permissions from the JSONField
        if isinstance(admin_role.permissions, dict):
            current_permissions = admin_role.permissions.get('permissions', [])
        elif isinstance(admin_role.permissions, list):
            current_permissions = admin_role.permissions
        else:
            current_permissions = []
        
        # Add category permissions if not already present
        category_permissions = [
            'category.create',
            'category.edit', 
            'category.delete',
            'category.view',
            'category.manage'
        ]
        
        # Add new permissions to existing ones
        updated_permissions = list(set(current_permissions + category_permissions))
        
        # Update the role with new permissions
        admin_role.permissions = {'permissions': updated_permissions}
        admin_role.save()
        
        print(f"Added category permissions to Administrator role: {category_permissions}")
        
    except Role.DoesNotExist:
        print("Administrator role not found - skipping category permission addition")


def remove_category_permissions(apps, schema_editor):
    """Remove category management permissions from Administrator role"""
    Role = apps.get_model('user', 'Role')
    
    try:
        admin_role = Role.objects.get(name='Administrator')
        
        # Get current permissions from the JSONField
        if isinstance(admin_role.permissions, dict):
            current_permissions = admin_role.permissions.get('permissions', [])
        elif isinstance(admin_role.permissions, list):
            current_permissions = admin_role.permissions
        else:
            current_permissions = []
        
        # Remove category permissions
        category_permissions = [
            'category.create',
            'category.edit', 
            'category.delete',
            'category.view',
            'category.manage'
        ]
        
        # Remove category permissions from existing ones
        updated_permissions = [perm for perm in current_permissions if perm not in category_permissions]
        
        # Update the role with updated permissions
        admin_role.permissions = {'permissions': updated_permissions}
        admin_role.save()
        
        print(f"Removed category permissions from Administrator role: {category_permissions}")
        
    except Role.DoesNotExist:
        print("Administrator role not found - skipping category permission removal")


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0011_add_first_login_date'),
    ]

    operations = [
        migrations.RunPython(
            add_category_permissions,
            remove_category_permissions,
        ),
    ]
