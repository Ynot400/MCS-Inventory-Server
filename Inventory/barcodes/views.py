
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import View
from Pages.form import SearchForm1
from Products.models import Product
from utils.generate_barcode import generate_barcode_and_save
from utils.generate_qrcode import generateQR
from utils.print_barcode import print_barcode

class CreateBarcode(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    def handle_no_permission(self):
        return redirect('home')
    def get(self, request):
       form = SearchForm1()
       return render(request, 'Dashboard/Create-barcode.html', {'form': form})
    def post(self, request):
      self.items = []
      if request.method == 'POST':
        if 'generateBarcode' in request.POST:
            product_id = request.POST.get('product_ID')
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Product not found'})
            product_name = product.title
            product_location = product.location_ID
            product_part = product.product_ID
            product_barcode = product.barcode
            generate_barcode_and_save(product_barcode, product_name, product_part, product_location)
            return JsonResponse({'status': 'success'})
        else:
          form = SearchForm1(request.POST)
        if form.is_valid():
          selectedOption = form.cleaned_data['inventory_field']
          if selectedOption == 'Show All':
            self.items = Product.objects.order_by('title')
            return render(request, 'Dashboard/Create-barcode.html', {'items': self.items, 'form': form})
          else:
            user_search_input = form.cleaned_data['search_field']
            if user_search_input:
              self.items = Product.objects.filter(**{f"{selectedOption}__contains": user_search_input})
            else:   # If search field is empty, show all products
              self.items = Product.objects.order_by('title')
        else:
          form = SearchForm1()
      return render(request, 'Dashboard/Create-barcode.html', {'items': self.items, 'form': form})

class PrintBarcode(UserPassesTestMixin, View):
   def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
   def handle_no_permission(self):
        return redirect('home')
   def get(self, request):
      form = SearchForm1()
      return render(request, 'Dashboard/print-barcode.html', {'form': form})
   def post(self, request):
      self.items = []
      if request.method == 'POST':
        if 'printBarcode' in request.POST:
            product_id = request.POST.get('product_ID')
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Product not found'})
            product_name = product.title
            try:
               print(f'Printing barcode for {product_name}')
               print_barcode(product_name)
               product.printed = True
               product.save()
               return JsonResponse({'status': 'success'})
            except Exception as e:
               return JsonResponse({'status': 'error', 'message': f'Error printing barcode: {e}'})
        else:
          form = SearchForm1(request.POST)
        if form.is_valid():
          selectedOption = form.cleaned_data['inventory_field']
          if selectedOption == 'Show All':
            self.items = Product.objects.order_by('title')
            return render(request, 'Dashboard/print-barcode.html', {'items': self.items, 'form': form})
          elif selectedOption == 'printed':
             self.items = Product.objects.filter(printed=False)
             printAll = True
             return render(request, 'Dashboard/print-barcode.html', {'items': self.items, 'form': form, 'printAll': printAll})
          elif selectedOption == 'date_created':
            self.items = Product.objects.order_by('-date_created')
          else:
            user_search_input = form.cleaned_data['search_field']
            if user_search_input:
              self.items = Product.objects.filter(**{f"{selectedOption}__contains": user_search_input})
            else:   # If search field is empty, show all products
              self.items = Product.objects.order_by('title')
        else:
          form = SearchForm1()
      return render(request, 'Dashboard/print-barcode.html', {'items': self.items, 'form': form})


class CreateQRCode(UserPassesTestMixin, View):
   def test_func(self):
        return self.request.user.is_superuser
   def handle_no_permission(self):
        return redirect('home')
   def get(self, request):
      return render(request, 'Dashboard/create-qr.html')
   def post(self, request):
      if request.method == 'POST' and 'generateQR' in request.POST:
         username = request.POST.get('username')
         password = request.POST.get('password')
         generateQR(username, password)
         return JsonResponse({'status': 'success'})
      else:
         return render(request, 'Dashboard/create-qr.html')

class ProductFinder(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff
    def handle_no_permission(self):
        return redirect('home')
    def get(self, request):
        return render(request, 'Dashboard/scan_barcode.html')

    def post(self, request):
        barcode2 = request.POST.get('scannedData', '')
        inv_barcode = int(barcode2) // 10
        product = None
        try:
            product = Product.objects.get(barcode=int(inv_barcode))
        except Product.DoesNotExist:
            try:
                product = Product.objects.get(manufacturer_barcode=int(barcode2))
            except Product.DoesNotExist:
                error = "Product does not exist."
                return render(request, 'Dashboard/scan_barcode.html', {'error': error})
            except ValueError:
                error = "The value received is of incorrect type."
                return render(request, 'Dashboard/scan_barcode.html', {'error': error})
        except ValueError:
            error = "The value received is of incorrect type."
            return render(request, 'Dashboard/scan_barcode.html', {'error': error})

        return render(request, 'Dashboard/quantity-adjuster.html', {'product': product})

 

   