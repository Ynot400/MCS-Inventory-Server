from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AdminPasswordChangeForm
from Products.models import Product 
from Pages.models import Search
from django.core.exceptions import ValidationError

class UserRegistrationAdminForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if ':' in username:
            raise ValidationError("Username cannot contain ':'")
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if ':' in password:
            raise ValidationError("Password cannot contain ':'")
        return password

class NoColonAdminPasswordChangeForm(AdminPasswordChangeForm):
     def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if ":" in password:
            raise ValidationError("Password cannot contain a colon (:) character.")
        return password


class UserRegisterForm(UserCreationForm):
  email = forms.EmailField()
  class Meta:
    model = User
    fields = ['username', 'email', 'password1', 'password2']

class ProductForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get('section')
        level = cleaned_data.get('level')
        vertical = cleaned_data.get('vertical')
        horizontal = cleaned_data.get('horizontal')

        # ensure that an accidental white space does not cause issues with product ID
        sanitizedPartNumber = self.cleaned_data.get('product_ID', None) 
        # strip() removes leading and trailing whitespace
        if sanitizedPartNumber is not None:
            cleaned_data['product_ID'] = sanitizedPartNumber.strip()
        # ensure that an accidental white space does not cause issues with manufacturer barcode
        sanitizedManufacturerBarcode = self.cleaned_data.get('manufacturer_barcode', None) 
        # strip() removes leading and trailing whitespace
        if sanitizedManufacturerBarcode is not None:
            cleaned_data['manufacturer_barcode'] = sanitizedManufacturerBarcode.strip()


        # Compose the location_ID
        location_id = f"{section}-{level}-{vertical}-{horizontal}"

         # Uniqueness check for location ID
        if Product.objects.filter(location_ID=location_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError({'This location ID is already assigned to another product.'})
        
        cleaned_data['location_ID'] = location_id

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.location_ID = self.cleaned_data['location_ID']
        if commit:
            instance.save()
        return instance

    def generate_section_pairs():
            pairs = [f"0{chr(i)}" for i in range(ord('A'), ord('Z')+1)]  # 0A to 0Z
            for i in range(ord('A'), ord('Z')+1):
                for j in range(ord('A'), ord('Z')+1):
                    if i == ord('H') and j == ord('W'):
                        continue
                    pairs.append(f"{chr(i)}{chr(j)}")
            return pairs

    def generate_level_pairs():
            pairs = [f"0{chr(i)}" for i in range(ord('A'), ord('Z')+1)]  # 0A to 0Z
            for i in range(ord('A'), ord('Z')+1):
                for j in range(ord('A'), ord('Z')+1):
                    pairs.append(f"{chr(i)}{chr(j)}")
            return pairs

    SECTION_CHOICES = [('HW', 'HW')] + [(val, val) for val in generate_section_pairs()]

    LEVEL_CHOICES = [(val, val) for val in generate_level_pairs()] 

    DIGIT_CHOICES = [(f"{i:02}", f"{i:02}") for i in range(100)]
    section = forms.ChoiceField(choices=SECTION_CHOICES, label="Section")
    level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Level")
    vertical = forms.ChoiceField(choices=DIGIT_CHOICES, label="Vertical")
    horizontal = forms.ChoiceField(choices=DIGIT_CHOICES, label="Horizontal")
    
    class Meta:
        model = Product
        fields = ['title', 'description', 'product_ID', 'manufacturer_barcode', 'quantity', 'min_quantity', 'max_quantity', 'vendor', 'high_priority', 'admin_field_price1', 'admin_field_price2']
        labels = {
                'title': 'Product Name',
                'description': 'Description',
                'product_ID': 'Part Number',
                'manufacturer_barcode': 'Manufacturer Barcode (if applicable)',
                'quantity': 'Quantity',
                'min_quantity': 'Minimum Quantity',
                'max_quantity': 'Maximum Quantity',
                'vendor': 'Vendor',
                'high_priority': 'Does this product have high priority?',
                'admin_field_price1': 'Retail',
                'admin_field_price2': 'Cost',
            }
    def __init__(self, *args, **kwargs):
            # Extract user from kwargs or provide a default

            self.user = kwargs.pop('user', None) or User.objects.get(username='default_admin')
          
            # Call the parent constructor
            super(ProductForm, self).__init__(*args, **kwargs)

            # Prepopulate location fields if editing existing product
            instance = kwargs.get('instance')
            if instance and instance.location_ID:
                parts = instance.location_ID.split('-')
                if len(parts) == 4:
                    self.fields['section'].initial = parts[0]
                    self.fields['level'].initial = parts[1]
                    self.fields['vertical'].initial = parts[2]
                    self.fields['horizontal'].initial = parts[3]


            # Conditionally include admin fields based on user permissions
            if not self.user.is_superuser:
                del self.fields['admin_field_price1']
                del self.fields['admin_field_price2']
            else:
                self.fields['admin_field_price1'].initial = ''
                self.fields['admin_field_price2'].initial = ''
                self.fields['admin_field_price1'].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'Enter retail price',
                })
                self.fields['admin_field_price2'].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'Enter cost price',
                })

            self.fields['description'].widget.attrs['placeholder'] = 'Enter product description and/or overstock information here.'

            self.fields['title'].widget.attrs.update({
                'rows': 1,
                'cols': 40,
                'style': 'resize:none;',
                'placeholder': 'Enter product name'
            })
            self.fields['vendor'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Enter vendor name',
                'rows': 1,
                'cols': 40,
                'style': 'resize:none;'
            })
            self.fields['product_ID'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Enter Part # or Secondary Identifier',
                'rows': 1,
                'cols': 40,
                'style': 'resize:none;'
            })

            self.fields['min_quantity'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Minimum stock level',
            })

            self.fields['max_quantity'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Maximum stock level',
            })
            self.fields['max_quantity'].initial = ''
            self.fields['min_quantity'].initial = ''




class ProductForm2(forms.ModelForm):
    SECTION_CHOICES = [('HW', 'HW')] + [(val, val) for val in ProductForm.generate_section_pairs()]
    LEVEL_CHOICES = [(val, val) for val in ProductForm.generate_level_pairs()]
    DIGIT_CHOICES = [(f"{i:02}", f"{i:02}") for i in range(100)]

    section = forms.ChoiceField(choices=SECTION_CHOICES, label="Section")
    level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Level")
    vertical = forms.ChoiceField(choices=DIGIT_CHOICES, label="Vertical")
    horizontal = forms.ChoiceField(choices=DIGIT_CHOICES, label="Horizontal")

    class Meta:
        model = Product
        fields = ['description']  # location_ID is constructed, not input directly

    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get('section')
        level = cleaned_data.get('level')
        vertical = cleaned_data.get('vertical')
        horizontal = cleaned_data.get('horizontal')

        location_id = f"{section}-{level}-{vertical}-{horizontal}"
        cleaned_data['location_ID'] = location_id
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.location_ID = self.cleaned_data['location_ID']
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        super(ProductForm2, self).__init__(*args, **kwargs)


        # Prepopulate location fields if editing existing product
        instance = kwargs.get('instance')
        if instance and instance.location_ID:
            parts = instance.location_ID.split('-')
            if len(parts) == 4:
                self.fields['section'].initial = parts[0]
                self.fields['level'].initial = parts[1]
                self.fields['vertical'].initial = parts[2]
                self.fields['horizontal'].initial = parts[3]


        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter description',
        })


SORT_CHOICES = [
    ('alphabetical', 'Product Order'),
    ('recent', 'Recently Added'),
    ('oldest', 'Oldest')
]

class SearchForm1(forms.Form):
    product_name = forms.CharField(label='Product Name', required=False)
    product_ID = forms.CharField(label='Part Number', required=False)

    # construct location_ID from section, level, vertical, horizontal
    SECTION_CHOICES = [('', '---')] + [('HW', 'HW')] + [(val, val) for val in ProductForm.generate_section_pairs()]
    LEVEL_CHOICES = [('', '---')] + [(val, val) for val in ProductForm.generate_level_pairs()]
    DIGIT_CHOICES = [('', '---')] + [(f"{i:02}", f"{i:02}") for i in range(100)]
    section = forms.ChoiceField(choices=SECTION_CHOICES, required=False, label="Section")
    level = forms.ChoiceField(choices=LEVEL_CHOICES, required=False, label="Level")
    vertical = forms.ChoiceField(choices=DIGIT_CHOICES, required=False, label="Vertical")
    horizontal = forms.ChoiceField(choices=DIGIT_CHOICES, required=False, label="Horizontal")

    # location_ID = forms.CharField(label='Location ID', required=False)
    vendor = forms.CharField(label='Vendor', required=False)
    
    sort_order = forms.ChoiceField(choices=SORT_CHOICES, required=False, label='Sort By')
    show_all = forms.BooleanField(label='Show All', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This sets it as checked by default only when no POST data is submitted
        if not self.is_bound:
            self.fields['show_all'].initial = True
        self.fields['sort_order'].widget.attrs.update({
            'onchange': 'document.getElementById("searchForm").submit();'
        })

        self.fields['product_name'].widget.attrs.update({
            'autocomplete': 'off',
        })



    def clean(self):
        cleaned_data = super().clean()
        show_all = cleaned_data.get('show_all')
            
        search_fields = any(
            cleaned_data.get(field)
            for field in ['product_name', 'product_ID', 'vendor', 'section', 'level', 'vertical', 'horizontal']
     )

        if not show_all and not search_fields:
            raise forms.ValidationError("Please enter at least one field to search, or check 'Show All'.")
        return cleaned_data