# Generated manually to approve existing users

from django.db import migrations


def approve_existing_users(apps, schema_editor):
    """Approve all existing users"""
    CustomUser = apps.get_model('user', 'CustomUser')
    CustomUser.objects.all().update(is_approved=True)


def reverse_approve_existing_users(apps, schema_editor):
    """Reverse operation - set all users as not approved"""
    CustomUser = apps.get_model('user', 'CustomUser')
    CustomUser.objects.all().update(is_approved=False)


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0009_add_user_approval_system'),
    ]

    operations = [
        migrations.RunPython(
            approve_existing_users,
            reverse_approve_existing_users,
        ),
    ]
