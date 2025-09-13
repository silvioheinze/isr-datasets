from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Dataset


@receiver(post_save, sender=Dataset)
def set_published_date(sender, instance, created, **kwargs):
    """Set published_at when dataset status changes to published"""
    if instance.status == 'published' and not instance.published_at:
        instance.published_at = timezone.now()
        # Save again to update the published_at field
        Dataset.objects.filter(pk=instance.pk).update(published_at=instance.published_at)
