# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .form import UserRegistrationAdminForm
from utils.generate_qrcode import generateQR

class CustomUserAdmin(UserAdmin):
    add_form = UserRegistrationAdminForm
    
    def save_model(self, request, obj, form, change):
      obj.is_staff = True
      raw_password = form.cleaned_data.get("password1")
      username = form.cleaned_data.get("username")
      generateQR(username, raw_password)
      super().save_model(request, obj, form, change)



admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)