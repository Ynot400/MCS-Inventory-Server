from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login
from .form import UserRegisterForm, SearchForm1
from Products.models import Product
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models.functions import Substr


def product_autocomplete(request):
    query = request.GET.get('q', '')
    matches = (
        Product.objects
        .filter(title__istartswith=query)
        .values_list('title', flat=True)
        .distinct()
        [:10]
    )
    return JsonResponse({'results': list(matches)})


def partNumber_autocomplete(request):
    query = request.GET.get('q', '')
    matches = (
        Product.objects
        .filter(product_ID__istartswith=query)
        .values_list('product_ID', flat=True)
        .distinct()
        [:10]
    )
    return JsonResponse({'results': list(matches)})



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
         return render(request, 'Dashboard/scan_barcode.html')
      else:
         return render(request, 'home.html')


class DashboardInventory(UserPassesTestMixin, View):
   def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
   def handle_no_permission(self):
        return redirect('home')
   items = None
   def get(self, request):
      form = SearchForm1()
      items = Product.objects.order_by('title')
      is_inventory_technician = request.user.groups.filter(name='Inventory Technician').exists()
      return render(request, 'Dashboard/inventory.html', {'items':items, 'form': form, 'is_inventory_technician': is_inventory_technician})
   def post(self, request):
    form = SearchForm1(request.POST)
    if form.is_valid():
        cd = form.cleaned_data

        if cd['show_all']:
            items = Product.objects.all()
        else:
            filters = {}
            if cd['product_name']:
                filters['title__icontains'] = cd['product_name']
            if cd['product_ID']:
                filters['product_ID__icontains'] = cd['product_ID']
            if cd['vendor']:
                filters['vendor__icontains'] = cd['vendor']

            # Begin with location annotations for partial filtering
            items = Product.objects.annotate(
                loc_section=Substr('location_ID', 1, 2),
                loc_level=Substr('location_ID', 4, 2),
                loc_vertical=Substr('location_ID', 7, 2),
                loc_horizontal=Substr('location_ID', 10, 2)
            )

            # Apply partial location filters
            if cd.get('section'):
                items = items.filter(loc_section=cd['section'])
            if cd.get('level'):
                items = items.filter(loc_level=cd['level'])
            if cd.get('vertical'):
                items = items.filter(loc_vertical=cd['vertical'])
            if cd.get('horizontal'):
                items = items.filter(loc_horizontal=cd['horizontal'])

            # Apply other filters (product name, vendor, etc.)
            items = items.filter(**filters)

        # Apply sorting
        sort_order = cd.get('sort_order')
        if sort_order == 'recent':
            items = items.order_by('-date_created')
        elif sort_order == 'oldest':
            items = items.order_by('date_created')
        elif sort_order == 'alphabetical':
            items = items.order_by('title')
    else:
        items = Product.objects.none()

    is_inventory_technician = request.user.groups.filter(name='Inventory Technician').exists()
    return render(request, 'Dashboard/inventory.html', {
        'items': items,
        'form': form,
        'is_inventory_technician': is_inventory_technician
    })


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
                      return render(request, 'Dashboard/scan_barcode.html')
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
      return render(request, 'Dashboard/scan_barcode.html')
    elif request.user.is_superuser:
      return render(request, 'Dashboard/dashboard1.html')
    return render(request, 'home.html')
