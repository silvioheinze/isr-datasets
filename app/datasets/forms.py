from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Dataset, DatasetCategory, DatasetVersion
from projects.models import Project

User = get_user_model()


class DatasetForm(forms.ModelForm):
    """Form for creating and editing datasets"""
    
    class Meta:
        model = Dataset
        fields = [
            'title', 'description', 'abstract', 'category', 'tags', 'keywords',
            'status', 'access_level', 'is_featured', 'license',
            'citation', 'doi', 'publishing_authority', 'uri_ref', 'contributors', 'related_datasets', 'project'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter dataset title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of the dataset'
            }),
            'abstract': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief summary of the dataset'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tags separated by commas'
            }),
            'keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Keywords for search (one per line)'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'access_level': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'license': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CC BY 4.0, MIT License'
            }),
            'citation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'How to cite this dataset'
            }),
            'doi': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digital Object Identifier'
            }),
            'publishing_authority': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., University of Vienna, Research Institute'
            }),
            'uri_ref': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/dataset-identifier'
            }),
            'contributors': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'related_datasets': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'project': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show featured checkbox to superusers
        if not (user and user.is_superuser):
            self.fields['is_featured'].widget = forms.HiddenInput()
        
        # Limit contributors to active users
        self.fields['contributors'].queryset = User.objects.filter(is_active=True)
        
        # Only show active categories
        self.fields['category'].queryset = DatasetCategory.objects.filter(is_active=True)
        
        # Configure related datasets queryset
        if self.instance.pk:
            # When editing, exclude the current dataset from related datasets
            self.fields['related_datasets'].queryset = Dataset.objects.exclude(pk=self.instance.pk)
        else:
            # When creating, show all datasets
            self.fields['related_datasets'].queryset = Dataset.objects.all()
        
        # Configure project queryset based on user access
        if user and user.is_authenticated:
            # Show projects the user owns or collaborates on
            accessible_projects = Project.objects.filter(
                Q(owner=user) | Q(collaborators=user) | Q(access_level='public')
            ).distinct()
            self.fields['project'].queryset = accessible_projects
        else:
            # No projects if user is not authenticated
            self.fields['project'].queryset = Project.objects.none()

    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        if tags:
            # Clean and validate tags
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tag_list) > 10:
                raise forms.ValidationError('Maximum 10 tags allowed.')
            return ', '.join(tag_list)
        return tags


class DatasetFilterForm(forms.Form):
    """Form for filtering datasets"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search datasets...'
        })
    )
    category = forms.ModelChoiceField(
        queryset=DatasetCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by tags...'
        })
    )
    access_level = forms.ChoiceField(
        choices=[('', 'All Access Levels')] + Dataset.ACCESS_LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-download_count', 'Most Downloaded'),
            ('title', 'Title A-Z'),
            ('-title', 'Title Z-A'),
        ],
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class DatasetCategoryForm(forms.ModelForm):
    """Form for creating and editing dataset categories"""
    
    class Meta:
        model = DatasetCategory
        fields = ['name', 'description', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Category description'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate names (excluding current instance)
            queryset = DatasetCategory.objects.filter(name__iexact=name)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('A category with this name already exists.')
        return name


class DatasetVersionForm(forms.ModelForm):
    """Form for creating new dataset versions"""
    
    # Add a choice field for input method
    input_method = forms.ChoiceField(
        choices=[
            ('upload', 'Upload File'),
            ('url', 'External URL')
        ],
        initial='upload',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = DatasetVersion
        fields = ['version_number', 'description', 'file', 'file_url', 'file_url_description', 'file_size_text']
        widgets = {
            'version_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1.1, 2.0, 1.2.3'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the changes in this version...'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.csv,.json,.xlsx,.xls,.txt,.zip,.tar.gz,.gpkg'
            }),
            'file_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/dataset.zip'
            }),
            'file_url_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe where the file is located (e.g., "GitHub repository", "University server", "Cloud storage")'
            }),
            'file_size_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 2.5 MB, 1.2 GB'
            })
        }

    def __init__(self, *args, **kwargs):
        self.dataset = kwargs.pop('dataset', None)
        super().__init__(*args, **kwargs)
        
        # Add help text for fields
        self.fields['version_number'].help_text = 'Use semantic versioning (e.g., 1.0, 1.1, 2.0)'
        self.fields['description'].help_text = 'Optional: Describe what changed in this version'
        self.fields['file'].help_text = 'Upload the new version file (CSV, JSON, Excel, TXT, ZIP, TAR.GZ, GPKG formats supported)'
        self.fields['file_url'].help_text = 'External URL where the file can be accessed'
        self.fields['file_url_description'].help_text = 'Optional: Describe where the file is located'
        self.fields['file_size_text'].help_text = 'Human-readable file size (e.g., "2.5 MB", "1.2 GB")'
        
        # Set initial field order
        self.fields['input_method'].label = 'File Input Method'

    def clean_version_number(self):
        version_number = self.cleaned_data.get('version_number')
        if version_number and self.dataset:
            # Check if version number already exists for this dataset
            if DatasetVersion.objects.filter(
                dataset=self.dataset, 
                version_number=version_number
            ).exists():
                raise forms.ValidationError(
                    f'Version {version_number} already exists for this dataset.'
                )
        return version_number

    def clean(self):
        cleaned_data = super().clean()
        input_method = cleaned_data.get('input_method')
        file = cleaned_data.get('file')
        file_url = cleaned_data.get('file_url')
        file_url_description = cleaned_data.get('file_url_description')
        file_size_text = cleaned_data.get('file_size_text')
        
        # Validate based on input method
        if input_method == 'upload':
            if not file:
                raise forms.ValidationError('Please upload a file when using the upload method.')
            if file_url:
                raise forms.ValidationError('Please do not provide a URL when uploading a file.')
            if file_size_text:
                raise forms.ValidationError('File size will be calculated automatically when uploading.')
                
            # Check file size (limit to 100MB)
            if file.size > 100 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 100MB.')
            
            # Update file_size field
            self.instance.file_size = file.size
            
        elif input_method == 'url':
            # Either URL or description must be provided (or both)
            if not file_url and not file_url_description:
                raise forms.ValidationError('Please provide either a URL or description (or both) when using the external URL method.')
            if file:
                raise forms.ValidationError('Please do not upload a file when using the external URL method.')
            if not file_size_text:
                raise forms.ValidationError('Please provide the file size when using external URL.')
            
            # Clear file field
            cleaned_data['file'] = None
            self.instance.file_size = 0
        
        return cleaned_data

    def clean_file(self):
        file = self.cleaned_data.get('file')
        input_method = self.cleaned_data.get('input_method')
        
        # Only validate file if upload method is selected
        if input_method == 'upload' and file:
            # Check file size (limit to 100MB)
            if file.size > 100 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 100MB.')
        
        return file


class DatasetCategoryForm(forms.ModelForm):
    """Form for creating and editing dataset categories"""
    
    class Meta:
        model = DatasetCategory
        fields = ['name', 'description', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this category...'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#007bff'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text for fields
        self.fields['name'].help_text = 'Unique name for the category'
        self.fields['description'].help_text = 'Optional description of the category'
        self.fields['color'].help_text = 'Color for the category badge'
        self.fields['is_active'].help_text = 'Whether this category is active and available for selection'

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for duplicate names (excluding current instance)
            queryset = DatasetCategory.objects.filter(name__iexact=name)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError('A category with this name already exists.')
        
        return name


class DatasetCategoryFilterForm(forms.Form):
    """Form for filtering categories"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search categories...'
        })
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
