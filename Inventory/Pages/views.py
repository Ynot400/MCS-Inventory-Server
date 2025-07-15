from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib.auth import authenticate, login
from .form import UserRegisterForm, SearchForm1
from Products.models import Product
from django.contrib.auth.mixins import UserPassesTestMixin
from utils.searchFormProductFilter import filter_products
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging
import traceback

logger = logging.getLogger("server")

def error_500(request):
    # Construct a message with useful context
    error_message = f"""
    [SERVER ERROR] Path: {request.path}
    Method: {request.method}
    User: {request.user if request.user.is_authenticated else "Anonymous"}
    Traceback:
    {traceback.format_exc()}
    """
    logger.error(error_message)
    return render(request, 'error/500.html', status=500)

def product_autocomplete(request):
    query = request.GET.get("q", "").strip()
    field = request.GET.get("field", "").strip()

    allowed_fields = {
        "title": "title",
        "product_ID": "product_ID",
        "vendor": "vendor",
    }

    if field not in allowed_fields or not query:
        return JsonResponse({"results": []})

    field_name = allowed_fields[field]

    # Try istartswith first
    startswith_filter = {f"{field_name}__istartswith": query}
    results = (
        Product.objects.filter(**startswith_filter)
        .values_list(field_name, flat=True)
        .distinct()
        [:10]
    )

    # Fallback if no startswith results
    if not results:
      contains_filter = {f"{field_name}__icontains": query}
      results = (
          Product.objects.filter(**contains_filter)
          .values_list(field_name, flat=True)
          .distinct()
          [:10]
      )

    return JsonResponse({"results": list(results)})



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
      form = SearchForm1(request.GET or None) # Either the search form was populated with GET data or it is empty

      if form.is_valid() and any(form.cleaned_data.values()):
          # print("Form goes here")
          items = filter_products(form)


          paginator = Paginator(items, 25)
          page = request.GET.get('page')

          try:
              paginated_items = paginator.page(page)
          except PageNotAnInteger:
              paginated_items = paginator.page(1)
          except EmptyPage:
              paginated_items = paginator.page(paginator.num_pages)
      else:
          paginated_items = None

      is_inventory_technician = request.user.groups.filter(name='Inventory Technician').exists()

      return render(request, 'Dashboard/inventory.html', {
          'items': paginated_items,
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
