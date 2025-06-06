# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .form import UserRegistrationAdminForm, NoColonAdminPasswordChangeForm
from utils.generate_qrcode import generateQR

class CustomUserAdmin(UserAdmin):
    # make sure that there is no colon, so that the QR code can be generated correctly
    add_form = UserRegistrationAdminForm # for the user registration form in the admin panel
    change_password_form = NoColonAdminPasswordChangeForm # for the password change form in the admin panel

    def save_model(self, request, obj, form, change):
      obj.is_staff = True
      if not change:
        raw_password = form.cleaned_data.get("password1")
        username = form.cleaned_data.get("username")
        print("Generating QR code for user:", username)
        print("Raw password:", raw_password)
        generateQR(username, raw_password) # generate QR code for the user
      super().save_model(request, obj, form, change)



admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)