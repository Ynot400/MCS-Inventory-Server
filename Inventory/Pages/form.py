from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from Products.models import Product 
from Pages.models import Search

class UserRegisterForm(UserCreationForm):
  email = forms.EmailField()
  class Meta:
    model = User
    fields = ['username', 'email', 'password1', 'password2']

class ProductForm(forms.ModelForm):
 
  class Meta:
    model = Product
    fields = ['title', 'description', 'location_ID', 'product_ID', 'manufacturer_barcode', 'quantity', 'vendor', 'high_priority', 'admin_field_price1', 'admin_field_price2']
    labels = {
            'title': 'Product Name',
            'description': 'Description',
            'location_ID': 'Location ID',
            'product_ID': 'Part Number',
            'manufacturer_barcode': 'Manufacturer Barcode (if applicable)',
            'quantity': 'Quantity',
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

      # Conditionally include admin fields based on user permissions
      if not self.user.is_superuser:
          del self.fields['admin_field_price1']
          del self.fields['admin_field_price2']
      else:
          self.fields['admin_field_price1'].initial = ''
          self.fields['admin_field_price2'].initial = ''
      self.fields['description'].widget.attrs['placeholder'] = 'Enter product description and/or overstock information here.'

class ProductForm2(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['location_ID', 'description']

    def __init__(self, *args, **kwargs):
        super(ProductForm2, self).__init__(*args, **kwargs)
        self.fields['location_ID'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter location id',
        })
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter description',
        })


class SearchForm1(forms.ModelForm):
   class Meta:
      model = Search
      fields = ['inventory_field', 'search_field']
   def __init__(self, *args, **kwargs):
    super(SearchForm1, self).__init__(*args, **kwargs)

    self.fields['inventory_field'].widget = forms.Select(choices=[('date_created', 'Recently Added'),('title', 'Product Name'), ('product_ID', 'Part Number'), ('location_ID', 'Location'), ('vendor', 'Vendor'), ('Show All', 'Show All'), ('printed', 'Not Yet Printed')])

    self.fields['inventory_field'].label = 'Search based on'
    self.fields['search_field'].label = 'Search for:'

