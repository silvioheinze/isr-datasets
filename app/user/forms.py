from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Role

CustomUser = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        required=False,
        empty_label="No role assigned"
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role')


class CustomUserEditForm(UserChangeForm):
    role = forms.ModelChoiceField(
        queryset=Role.objects.filter(is_active=True),
        required=False,
        empty_label="No role assigned"
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role')


class UserProfileForm(forms.ModelForm):
    """Form for user profile information"""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = _('First Name')
        self.fields['last_name'].label = _('Last Name')


class UserSettingsForm(forms.ModelForm):
    """Form for user account settings including language preference"""
    
    class Meta:
        model = CustomUser
        fields = ['language']
        widgets = {
            'language': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['language'].label = _('Interface Language')
        self.fields['language'].help_text = _('Choose your preferred language for the interface')


class DataExportForm(forms.Form):
    """Form for requesting data export"""
    
    EXPORT_FORMATS = [
        ('json', _('JSON')),
        ('csv', _('CSV')),
        ('xml', _('XML')),
    ]
    
    format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='json',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Export Format'),
        help_text=_('Choose the format for your data export')
    )
    
    include_datasets = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Include Datasets'),
        help_text=_('Include your datasets in the export')
    )
    
    include_projects = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Include Projects'),
        help_text=_('Include your projects in the export')
    )
    
    include_activity = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Include Activity Log'),
        help_text=_('Include your activity and download history')
    )


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'description', 'permissions']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'permissions': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter permissions as JSON array, e.g.: ["user.view", "user.edit", "user.delete"]'}),
        }

    def clean_permissions(self):
        permissions = self.cleaned_data.get('permissions')
        if isinstance(permissions, str):
            import json
            try:
                permissions = json.loads(permissions)
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for permissions")
        
        if not isinstance(permissions, dict):
            permissions = {'permissions': permissions if isinstance(permissions, list) else []}
        
        return permissions


class RoleFilterForm(forms.Form):
    """Form for filtering roles in the role list view"""
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search by name'}))
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('True', 'Active'), ('False', 'Inactive')],
        required=False,
        initial=''
    )