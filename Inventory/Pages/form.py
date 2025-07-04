from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AdminPasswordChangeForm
from Products.models import Product 
from Pages.models import Search
from django.core.exceptions import ValidationError
from jobtickets.models import JobTicket

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
        is_structured = cleaned_data.get('is_structured', True)

        # Ensure that min and max quantities are logical
        minQuantity = cleaned_data.get('min_quantity', 0)
        maxQuantity = cleaned_data.get('max_quantity', 1)

        if maxQuantity < minQuantity:
            self.add_error('max_quantity', "Maximum quantity must be greater than minimum quantity.")

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


        # Validation based on is_structured
        if is_structured:
            if not vertical or not horizontal:
                raise ValidationError("Structured (cubby) locations require vertical and horizontal fields.")
        else:
            vertical = horizontal = 'XX' # Default values for unstructured locations

        # Check uniqueness (only for structured positions)
        if is_structured:
            exists = Product.objects.filter(
                section=section,
                level=level,
                vertical=vertical,
                horizontal=horizontal,
                is_structured=True
            ).exclude(pk=self.instance.pk).exists()
            if exists:
                raise ValidationError(f"Cubby location {section}-{level}-{vertical}-{horizontal} is already assigned to another product.")

        cleaned_data['vertical'] = vertical
        cleaned_data['horizontal'] = horizontal
        cleaned_data['is_structured'] = is_structured

        return cleaned_data

    def save(self, commit=True):
        print("Saving product with location:", self.cleaned_data['section'], self.cleaned_data['level'], self.cleaned_data['vertical'], self.cleaned_data['horizontal'], self.cleaned_data['is_structured'])
        instance = super().save(commit=False)
        instance.section = self.cleaned_data['section']
        instance.level = self.cleaned_data['level']
        instance.vertical = self.cleaned_data['vertical']
        instance.horizontal = self.cleaned_data['horizontal']
        instance.is_structured = self.cleaned_data['is_structured']
        print("Product location:", instance.section, instance.level, instance.vertical, instance.horizontal, instance.is_structured)
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

    DIGIT_CHOICES = [('', 'XX')] + [(f"{i:02}", f"{i:02}") for i in range(1, 100)]
    section = forms.ChoiceField(choices=SECTION_CHOICES, label="Section")
    level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Level")
    vertical = forms.ChoiceField(choices=DIGIT_CHOICES, label="Vertical")
    horizontal = forms.ChoiceField(choices=DIGIT_CHOICES, label="Horizontal")
   
    class Meta:
        model = Product
        fields = ['title', 'description', 'product_ID', 'manufacturer_barcode', 'quantity', 'min_quantity', 'max_quantity', 'vendor', 'high_priority', 'admin_field_price1', 'admin_field_price2', 'is_structured']
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
                'is_structured': 'Is this product in a cubby?',
            }
    def __init__(self, *args, **kwargs):
            # Extract user from kwargs or provide a default

            self.user = kwargs.pop('user', None) or User.objects.get(username='default_admin')
          
            # Call the parent constructor
            super(ProductForm, self).__init__(*args, **kwargs)

            # Prepopulate location fields if editing existing product
            instance = kwargs.get('instance')

            # this will prepopulate the location_ID field if it exists
            if instance:
                self.fields['section'].initial = instance.section
                self.fields['level'].initial = instance.level
                self.fields['vertical'].initial = instance.vertical
                self.fields['horizontal'].initial = instance.horizontal
                self.fields['is_structured'].initial = instance.is_structured
            else:
                self.fields['is_structured'].initial = True  # Default to structured if not provided


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
                    'onwheel': 'this.blur()',
                })
                self.fields['admin_field_price2'].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'Enter cost price',
                    'onwheel': 'this.blur()',
                })


                # if self.data.get('is_structured') != 'on':
                #     # Shelf = unstructured: vertical/horizontal are not required
                self.fields['vertical'].required = False
                self.fields['horizontal'].required = False
                # else:
                #     # Cubby = structured: enforce required
                #     self.fields['vertical'].required = True
                #     self.fields['horizontal'].required = True

            self.fields['description'].widget.attrs['placeholder'] = 'Enter product description and/or overstock information here.'

            self.fields['title'].widget.attrs.update({
                'rows': 1,
                'cols': 40,
                'style': 'resize:none;',
                'placeholder': 'Enter product name'
            })
            # retrieve the unique vendor names that have been created
            unique_vendors = Product.objects.exclude(vendor__isnull=True).exclude(vendor='') \
                .values_list('vendor', flat=True).distinct()
            
            self.fields['vendor'].widget.attrs.update({
                'class': 'form-control',
                'list': 'vendor-options',
                'placeholder': 'Select Vendor or Create New',
                # 'rows': 1,
                # 'cols': 40,
                # 'style': 'resize:none;'
            })

            self.vendor_datalist = sorted(unique_vendors)
            # print("Loaded vendors:", list(unique_vendors))

            self.fields['product_ID'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Enter Part # or Secondary Identifier',
                'rows': 1,
                'cols': 40,
                'style': 'resize:none;'
            })

            self.fields['min_quantity'].widget.attrs.update({
                'class': 'form-control',
                'onwheel': 'this.blur()',
                'placeholder': 'Minimum stock level',
            })

            self.fields['max_quantity'].widget.attrs.update({
                'class': 'form-control',
                'onwheel': 'this.blur()',
                'placeholder': 'Maximum stock level',
            })
            self.fields['quantity'].widget.attrs.update({
                'class': 'form-control',
                'onwheel': 'this.blur()',
                'placeholder': 'Current stock level',
            })
            self.fields['max_quantity'].initial = ''
            self.fields['min_quantity'].initial = ''






class ProductForm2(forms.ModelForm):
    SECTION_CHOICES = [('HW', 'HW')] + [(val, val) for val in ProductForm.generate_section_pairs()]
    LEVEL_CHOICES = [(val, val) for val in ProductForm.generate_level_pairs()]
    DIGIT_CHOICES = [('', 'XX')] + [(f"{i:02}", f"{i:02}") for i in range(1, 100)]

    section = forms.ChoiceField(choices=SECTION_CHOICES, label="Section")
    level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Level")
    vertical = forms.ChoiceField(choices=DIGIT_CHOICES, label="Vertical")
    horizontal = forms.ChoiceField(choices=DIGIT_CHOICES, label="Horizontal")

    class Meta:
        model = Product
        fields = ['description', 'is_structured']  # location_ID is constructed, not input directly
        labels = {
            'description': 'Description',
            'is_structured': 'Is this product in a cubby or on a shelf?',
        }

    def clean(self):
        cleaned_data = super().clean()
        section = cleaned_data.get('section')
        level = cleaned_data.get('level')
        vertical = cleaned_data.get('vertical')
        horizontal = cleaned_data.get('horizontal')
        is_structured = cleaned_data.get('is_structured', True)

        # Validation based on is_structured
        if is_structured:
            if not vertical or not horizontal:
                raise ValidationError("Structured (cubby) locations require vertical and horizontal fields.")
        else:
            vertical = horizontal = 'XX'

        # Check uniqueness (only for structured positions)
        if is_structured:
            exists = Product.objects.filter(
                section=section,
                level=level,
                vertical=vertical,
                horizontal=horizontal,
                is_structured=True
            ).exclude(pk=self.instance.pk).exists()
            if exists:
                raise ValidationError(f"Cubby location {section}-{level}-{vertical}-{horizontal} is already assigned to another product.")

        cleaned_data['vertical'] = vertical
        cleaned_data['horizontal'] = horizontal
        cleaned_data['is_structured'] = is_structured

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.section = self.cleaned_data['section']
        instance.level = self.cleaned_data['level']
        instance.vertical = self.cleaned_data['vertical']
        instance.horizontal = self.cleaned_data['horizontal']
        instance.is_structured = self.cleaned_data['is_structured']
        if commit:
            instance.save()
        return instance

    def __init__(self, *args, **kwargs):
        super(ProductForm2, self).__init__(*args, **kwargs)


        # Prepopulate location fields if editing existing product
        instance = kwargs.get('instance')
        # this will prepopulate the location_ID field if it exists
        if instance:
            self.fields['section'].initial = instance.section
            self.fields['level'].initial = instance.level
            self.fields['vertical'].initial = instance.vertical
            self.fields['horizontal'].initial = instance.horizontal
            self.fields['is_structured'].initial = instance.is_structured
        else:
            self.fields['is_structured'].initial = True  # Default to structured if not provided



        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter product description and/or overstock information here.',
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
       
        self.fields['sort_order'].widget.attrs.update({
            'onchange': 'document.getElementById("searchForm").submit();'
        })

        self.fields['product_name'].widget.attrs.update({
            'autocomplete': 'off',
        })
        self.fields['product_ID'].widget.attrs.update({
            'autocomplete': 'off',
        })
        self.fields['vendor'].widget.attrs.update({
            'autocomplete': 'off',
        })
        self.fields['section'].widget.attrs.update({
            'style': 'height: 30px; width: 48px;'
        })
        self.fields['level'].widget.attrs.update({
            'style': 'height: 30px; width: 48px;'
        })
        self.fields['vertical'].widget.attrs.update({
            'style': 'height: 30px; width: 40px;'
        })
        self.fields['horizontal'].widget.attrs.update({
            'style': 'height: 30px; width: 40px;'
        })



    def clean(self):
        cleaned_data = super().clean()
        show_all = cleaned_data.get('show_all')
            
        search_fields = any(
            cleaned_data.get(field)
            for field in ['product_name', 'product_ID', 'vendor', 'section', 'level', 'vertical', 'horizontal']
        )

        # if show_all is None:

        if not show_all and not search_fields:
            raise forms.ValidationError("Please enter at least one field to search, or check 'Show All'.")
        return cleaned_data
    

class JobTicketForm(forms.ModelForm):
    class Meta:
        model = JobTicket
        fields = [
            'status',
            'genre',
            'custom_genre',
            'customer_name',
            'boat_name',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'genre': forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleCustomGenreField(this);'}),
            'custom_genre': forms.TextInput(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'boat_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        genre = cleaned_data.get('genre')
        custom_genre = cleaned_data.get('custom_genre')

        if genre == 'Custom' and not custom_genre:
            self.add_error('custom_genre', "Please enter a custom genre.")
        return cleaned_data