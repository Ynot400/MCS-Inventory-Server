from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login
from .form import UserRegisterForm, SearchForm1
from Products.models import Product
from django.contrib.auth.mixins import UserPassesTestMixin

class Dashboard(UserPassesTestMixin, View):
   def test_func(self):
        return self.request.user.is_staff
   def handle_no_permission(self):
        return redirect('home')
   def get(self, request):
      if request.user.groups.filter(name='Inventory Technician').exists():
        return render(request, 'Dashboard/dashboard2.html')
      elif request.user.is_superuser:
        return render(request, 'Dashboard/dashboard1.html')
      elif request.user.groups.filter(name='Shop Technician').exists():
         return render(request, 'Dashboard/dashboard3.html')


class DashboardInventory(UserPassesTestMixin, View):
   def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
   def handle_no_permission(self):
        return redirect('home')
   items = None
   def get(self, request):
      form = SearchForm1()
      # self.items = Product.objects.order_by('title')
      is_inventory_technician = request.user.groups.filter(name='Inventory Technician').exists()
      return render(request, 'Dashboard/inventory.html', {'items':self.items, 'form': form, 'is_inventory_technician': is_inventory_technician})
   def post(self, request):
      if request.method == 'POST':
        form = SearchForm1(request.POST)
        if form.is_valid():
          selectedOption = form.cleaned_data['inventory_field']
          if selectedOption == 'Show All':
            self.items = Product.objects.order_by('title')
            return render(request, 'Dashboard/inventory.html', {'items': self.items, 'form': form})
          elif selectedOption == 'date_created':
            self.items = Product.objects.order_by('-date_created')
          elif selectedOption == 'printed':
             self.items = Product.objects.filter(printed=False)
          else:
            user_search_input = form.cleaned_data['search_field']
            if user_search_input:
              self.items = Product.objects.filter(**{f"{selectedOption}__contains": user_search_input})
            else:   # If search field is empty, show all products
              self.items = Product.objects.order_by('title')
        else:
          form = SearchForm1()
      is_inventory_technician = request.user.groups.filter(name='Inventory Technician').exists()
      return render(request, 'Dashboard/inventory.html', {'items': self.items, 'form': form, 'is_inventory_technician': is_inventory_technician})


class QRCodeLogin(View):
    def get(self, request):
        return render(request, 'QRCode_login.html')

    def post(self, request):
        if request.method == 'POST':
            qr_data = request.POST.get('scannedData', '')
            try:
                username, password = qr_data.split(':')
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    login(request, user)
                    if user.groups.filter(name='Inventory Technician').exists():
                      return render(request, 'Dashboard/dashboard2.html')
                    elif user.groups.filter(name='Shop Technician').exists():
                      return render(request, 'Dashboard/dashboard3.html')
                    elif user.is_superuser:
                      return render(request, 'Dashboard/dashboard1.html')
                else:
                    return render(request, 'QRCode_login.html', {'error': 'Invalid username or password'})

            except Exception as e:
                return render(request, 'QRCode_login.html', {'error': e})

class SignUpView(View):
  def get(self, request):
      form = UserRegisterForm()
      return render(request, 'signup.html', {'form': form})
  def post(self, request):
      form = UserRegisterForm(request.POST)
      if form.is_valid():
        form.save()
        user = authenticate(
          username=form.cleaned_data['username'],
          password=form.cleaned_data['password1']
        )
        login(request, user)
        return redirect('dashboard')
      return render(request, 'signup.html', {'form': form})


class ScanBarcode(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff
    def handle_no_permission(self):
        return redirect('home')
    def get(self, request):
      return render(request, 'Dashboard/scan_barcode.html')
  
  

class home_View(View):
  def get(self, request):
    if request.user.groups.filter(name='Inventory Technician').exists():
      return render(request, 'Dashboard/dashboard2.html')
    elif request.user.groups.filter(name='Shop Technician').exists():
      return render(request, 'Dashboard/dashboard3.html')
    elif request.user.is_superuser:
      return render(request, 'Dashboard/dashboard1.html')
    return render(request, 'home.html')
