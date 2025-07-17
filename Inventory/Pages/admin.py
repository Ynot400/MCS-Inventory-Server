# Pages/admin.py - Enhanced version with security restrictions
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django import forms
from .form import UserRegistrationAdminForm, NoColonAdminPasswordChangeForm
from utils.generate_qrcode import generateQR


class RestrictedUserForm(ModelForm):
    """Custom form for User model with group restrictions"""
    
    # Define groups as a separate field that won't be handled by Django's m2m system
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="No Group",
        help_text="Select a single group for this user. Superusers cannot have groups.",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = '__all__'
        # Exclude groups from Meta so Django doesn't try to handle it automatically
        exclude = ['groups', 'user_permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove user_permissions field if it somehow gets added
        if 'user_permissions' in self.fields:
            del self.fields['user_permissions']
        
        # Remove is_staff and is_active fields (always True)
        if 'is_staff' in self.fields:
            del self.fields['is_staff']
        if 'is_active' in self.fields:
            del self.fields['is_active']
        
        # Make password field read-only with link to change password
        if 'password' in self.fields:
            self.fields['password'].help_text = (
                'Raw passwords are not stored, so there is no way to see this '
                'user\'s password, but you can change the password using '
                '<a href="../password/">this form</a>.'
            )
            self.fields['password'].widget = forms.TextInput(attrs={
                'readonly': True,
                'class': 'vTextField readonly-field',
                'style': 'background-color: #f5f5f5;'
            })
        
        # Set current group if editing an existing user
        if self.instance and self.instance.pk:
            current_group = self.instance.groups.first()
            self.fields['groups'].initial = current_group
            
            # Style the groups field if user is superuser
            if self.instance.is_superuser:
                self.fields['groups'].widget.attrs.update({
                    'style': 'opacity: 0.6; background-color: #f5f5f5;'
                })

    def clean(self):
        cleaned_data = super().clean()
        is_superuser = cleaned_data.get('is_superuser', False)
        selected_group = cleaned_data.get('groups')
        
        # Prevent superusers from having groups
        if is_superuser and selected_group:
            raise ValidationError({
                'groups': 'Superusers cannot be assigned to groups. Please uncheck "Superuser status" or remove the group assignment.'
            })
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Force is_staff and is_active to True
        user.is_staff = True
        user.is_active = True
        
        if commit:
            user.save()
            # Handle groups after save
            self.save_groups()
        
        return user
    
    def save_groups(self):
        """Handle group assignment manually"""
        user = self.instance
        selected_group = self.cleaned_data.get('groups')
        
        # Clear all existing groups first
        user.groups.clear()
        
        # Add the selected group if any and user is not superuser
        if selected_group and not user.is_superuser:
            user.groups.add(selected_group)
    
    def save_m2m(self):
        """Override save_m2m since we handle groups manually"""
        # We handle groups in save_groups(), so nothing to do here
        pass


class CustomUserAdmin(UserAdmin):
    """Enhanced UserAdmin with security restrictions"""
    
    # Use custom forms
    form = RestrictedUserForm
    add_form = UserRegistrationAdminForm
    change_password_form = NoColonAdminPasswordChangeForm

    # Remove user_permissions and staff/active from all fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_superuser', 'groups')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'is_superuser', 'groups'),
        }),
    )

    # Remove user_permissions from list displays and filters
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_superuser', 'get_user_group')
    list_filter = ('is_superuser', 'date_joined', 'groups')
    

    
    def get_user_group(self, obj):
        """Display the user's group (since they can only have one)"""
        group = obj.groups.first()
        return group.name if group else 'No Group'
    get_user_group.short_description = 'Group'
    get_user_group.admin_order_field = 'groups__name'

    def save_model(self, request, obj, form, change):
        """Enhanced save with QR code generation and validation"""
        
        # Force is_staff and is_active to True for all users
        obj.is_staff = True
        obj.is_active = True
        
        # Generate QR code for new users
        if not change:
            raw_password = form.cleaned_data.get("password1")
            username = form.cleaned_data.get("username")
            if raw_password and username:
                print("Generating QR code for user:", username)
                generateQR(username, raw_password)
        
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Override save_related to handle our custom group logic"""
        # Handle groups first
        form.save_groups()
        
        # Call the parent method for any other related objects (excluding groups)
        # We need to prevent the parent from trying to save groups
        try:
            # Temporarily remove groups from the form's m2m fields if it exists
            original_save_m2m = getattr(form, '_save_m2m', None)
            
            # Set a custom save_m2m that does nothing
            form._save_m2m = lambda: None
            
            # Call parent save_related
            super().save_related(request, form, formsets, change)
            
        finally:
            # Restore original save_m2m if it existed
            if original_save_m2m:
                form._save_m2m = original_save_m2m

    def get_form(self, request, obj=None, **kwargs):
        """Override to use custom form"""
        kwargs['form'] = self.form if obj else self.add_form
        return super().get_form(request, obj, **kwargs)


class RestrictedGroupAdmin(admin.ModelAdmin):
    """Group admin that prevents access through URL manipulation"""
    
    def has_module_permission(self, request):
        """Hide Groups from admin index"""
        return False
    
    def has_view_permission(self, request, obj=None):
        """Prevent viewing groups"""
        return False
    
    def has_add_permission(self, request):
        """Prevent adding groups"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent changing groups"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting groups"""
        return False


# Unregister the default admin classes
admin.site.unregister(User)
admin.site.unregister(Group)

# Register our custom admin classes
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, RestrictedGroupAdmin)