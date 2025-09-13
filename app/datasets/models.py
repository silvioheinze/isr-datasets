from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField

User = get_user_model()


class DatasetCategory(models.Model):
    """Category model for organizing datasets"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Dataset Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Dataset(models.Model):
    """Main dataset model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
        ('private', 'Private'),
    ]
    
    ACCESS_LEVEL_CHOICES = [
        ('public', 'Public'),
        ('restricted', 'Restricted'),
        ('private', 'Private'),
    ]

    history = AuditlogHistoryField()
    
    # Basic information
    title = models.CharField(max_length=200)
    description = models.TextField()
    abstract = models.TextField(blank=True, help_text='Short summary of the dataset')
    
    # Metadata
    category = models.ForeignKey(
        DatasetCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='datasets'
    )
    tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags')
    keywords = models.TextField(blank=True, help_text='Keywords for search')
    
    # Access and permissions
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVEL_CHOICES, default='public')
    is_featured = models.BooleanField(default=False)
    
    # Ownership and attribution
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='owned_datasets'
    )
    contributors = models.ManyToManyField(
        User, 
        blank=True, 
        related_name='contributed_datasets',
        help_text='Users who contributed to this dataset'
    )
    
    # Related datasets
    related_datasets = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='related_to',
        help_text='Other datasets that are related to this one'
    )
    
    # Project association
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='datasets',
        verbose_name=_("Project"),
        help_text=_("The research project this dataset is associated with")
    )
    
    # License and citation
    license = models.CharField(max_length=100, blank=True)
    citation = models.TextField(blank=True, help_text='How to cite this dataset')
    doi = models.CharField(max_length=100, blank=True, help_text='Digital Object Identifier')
    
    
    # Statistics
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'access_level']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Return human-readable file size"""
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = self.file_size
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024
            i += 1
        
        return f"{size:.1f} {size_names[i]}"

    def get_tags_list(self):
        """Return tags as a list"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def is_accessible_by(self, user):
        """Check if user can access this dataset"""
        if self.access_level == 'public':
            return True
        elif self.access_level == 'restricted':
            return user.is_authenticated
        elif self.access_level == 'private':
            return user == self.owner or user.is_superuser
        return False


class DatasetVersion(models.Model):
    """Version control for datasets"""
    dataset = models.ForeignKey(
        Dataset, 
        on_delete=models.CASCADE, 
        related_name='versions'
    )
    version_number = models.CharField(max_length=20)
    description = models.TextField(blank=True, help_text='Changes in this version')
    file = models.FileField(upload_to='datasets/versions/%Y/%m/%d/', blank=True, null=True)
    file_size = models.BigIntegerField(default=0)
    file_url = models.URLField(blank=True, help_text='External URL to the file')
    file_url_description = models.TextField(blank=True, help_text='Description of the external file location')
    file_size_text = models.CharField(max_length=100, blank=True, help_text='Human-readable file size (e.g., "2.5 MB", "1.2 GB")')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['dataset', 'version_number']

    def __str__(self):
        return f"{self.dataset.title} v{self.version_number}"
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if self.file_size_text:
            return self.file_size_text
        elif self.file_size > 0:
            size_names = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            size = self.file_size
            
            while size >= 1024 and i < len(size_names) - 1:
                size /= 1024
                i += 1
            
            return f"{size:.1f} {size_names[i]}"
        return "Unknown size"
    
    def has_file(self):
        """Check if version has either uploaded file, external URL, or URL description"""
        return bool(self.file or self.file_url or self.file_url_description)


class DatasetDownload(models.Model):
    """Track dataset downloads"""
    dataset = models.ForeignKey(
        Dataset, 
        on_delete=models.CASCADE, 
        related_name='downloads'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['dataset', 'downloaded_at']),
            models.Index(fields=['user', 'downloaded_at']),
        ]

    def __str__(self):
        user_info = self.user.username if self.user else 'Anonymous'
        return f"{self.dataset.title} - {user_info}"


# Register models for audit logging
auditlog.register(Dataset)
auditlog.register(DatasetCategory)
auditlog.register(DatasetVersion)
auditlog.register(DatasetDownload)