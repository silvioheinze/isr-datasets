# Generated manually for API key support

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user', '0013_disable_email_notifications_by_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='A descriptive name for this API key (e.g., "My Script", "Production API")', max_length=100, verbose_name='Name')),
                ('key', models.CharField(help_text='The API key value (shown only once when created)', max_length=64, unique=True, verbose_name='API Key')),
                ('prefix', models.CharField(help_text='First 8 characters of the key for identification', max_length=8, verbose_name='Key Prefix')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this API key is active and can be used', verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this API key was created', verbose_name='Created At')),
                ('last_used_at', models.DateTimeField(blank=True, help_text='When this API key was last used', null=True, verbose_name='Last Used At')),
                ('expires_at', models.DateTimeField(blank=True, help_text='Optional expiration date for this API key', null=True, verbose_name='Expires At')),
                ('user', models.ForeignKey(help_text='The user who owns this API key', on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'API Key',
                'verbose_name_plural': 'API Keys',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='apikey',
            index=models.Index(fields=['key'], name='user_apikey_key_idx'),
        ),
        migrations.AddIndex(
            model_name='apikey',
            index=models.Index(fields=['user', 'is_active'], name='user_apikey_user_active_idx'),
        ),
    ]

