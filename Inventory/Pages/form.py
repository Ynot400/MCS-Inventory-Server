from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm, AdminPasswordChangeForm
from Products.models import Product 
from Pages.models import Search
from django.core.exceptions import ValidationError
from jobtickets.models import JobTicket, JobTicketItem



class UserRegistrationAdminForm(UserCreationForm):
    """Enhanced user registration form with group restrictions"""
    
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="No Group",
        help_text="Select a single group for this user. Cannot be set if user is a superuser.",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_superuser = forms.BooleanField(
        required=False,
        label="Superuser status",
        help_text="Designates that this user has all permissions on the program. Superusers cannot be assigned to groups.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'is_superuser', 'groups']
        # Exclude groups from automatic m2m handling
        exclude = ['user_permissions']

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

    def clean(self):
        cleaned_data = super().clean()
        is_superuser = cleaned_data.get('is_superuser', False)
        selected_group = cleaned_data.get('groups')
        
        # Prevent superusers from having groups
        if is_superuser and selected_group:
            raise ValidationError({
                'groups': 'Superusers cannot be assigned to groups.'
            })
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Force is_staff to True for all users (as per requirement)
        user.is_staff = True
        
        # Set superuser status from form
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        
        if commit:
            user.save()
            # Groups will be handled in save_related method of admin
        
        return user
    
    def save_groups(self):
        """Handle group assignment for add form"""
        user = self.instance
        selected_group = self.cleaned_data.get('groups')
        
        # Clear all existing groups first
        user.groups.clear()
        
        # Add the selected group if any and user is not superuser
        if selected_group and not user.is_superuser:
            user.groups.add(selected_group)


class NoColonAdminPasswordChangeForm(AdminPasswordChangeForm):
    """Enhanced password change form with colon restriction"""
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if ":" in password:
            raise ValidationError("Password cannot contain a colon (:) character.")
        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError("The two password fields didn't match.")
            if ":" in password2:
                raise ValidationError("Password cannot contain a colon (:) character.")
        
        return password2

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
    ('recent', 'Recently Added'),
    ('oldest', 'Oldest'),
    ('alphabetical', 'Product Order'),
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
        
        # data = args[0] if args else kwargs.get('data')
        # if not data:
        #     self.fields['show_all'].initial = True

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
        custom_genre = cleaned_data.get('custom_genre', None)

        if genre == 'Custom' and not custom_genre:
            self.add_error('custom_genre', "Please enter a custom genre.")
        return cleaned_data
    
    # Add this to your jobtickets/views.py or create a forms.py file in jobtickets


class CustomPartForm(forms.ModelForm):
    class Meta:
        model = JobTicketItem
        fields = ['custom_part_name', 'custom_part_description', 'custom_part_cost', 'quantity_used']
        widgets = {
            'custom_part_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter part name',
                'required': True
            }),
            'custom_part_description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Enter part description (optional)'
            }),
            'custom_part_cost': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01', 
                'placeholder': '0.00',
                'min': '0'
            }),
            'quantity_used': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1', 
                'value': '1'
            }),
        }
        labels = {
            'custom_part_name': 'Part Name',
            'custom_part_description': 'Description',
            'custom_part_cost': 'Cost per Unit ($)',
            'quantity_used': 'Quantity',
        }

    def clean(self):
        cleaned_data = super().clean()
        custom_part_name = cleaned_data.get('custom_part_name')
        
        if not custom_part_name or not custom_part_name.strip():
            raise forms.ValidationError("Part name is required for custom parts.")
        
        return cleaned_data

    def clean_custom_part_cost(self):
        cost = self.cleaned_data.get('custom_part_cost')
        if cost is not None and cost < 0:
            raise forms.ValidationError("Cost cannot be negative.")
        return cost

    def clean_quantity_used(self):
        quantity = self.cleaned_data.get('quantity_used')
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be at least 1.")
        return quantity