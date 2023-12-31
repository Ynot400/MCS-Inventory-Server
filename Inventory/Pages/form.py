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
    fields = ['title', 'location_ID', 'product_ID', 'quantity', 'vendor', 'admin_field_price1', 'admin_field_price2']
    labels = {
            'title': 'Product Name',
            'location_ID': 'Location ID',
            'product_ID': 'Part Number',
            'quantity': 'Quantity',
            'vendor': 'Vendor',
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

class SearchForm(forms.ModelForm):
   class Meta:
      model = Search
      fields = ['inventory_field', 'search_field']
   def __init__(self, *args, **kwargs):
    super(SearchForm, self).__init__(*args, **kwargs)

    self.fields['inventory_field'].widget = forms.Select(choices=[('title', 'Product Name'), ('product_ID', 'Product ID'), ('location_ID', 'Location'), ('vendor', 'Vendor'), ('Show All', 'Show All')])

    self.fields['inventory_field'].label = 'Search based on'
    self.fields['search_field'].label = 'Search for:'