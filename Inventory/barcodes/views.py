
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from Pages.form import SearchForm1
from Products.models import Product
from utils.generate_barcode import generate_barcode_and_save
from utils.generate_qrcode import generateQR
from utils.print_barcode import print_barcode

class CreateBarcode(LoginRequiredMixin, View):
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
            product_barcode = product.barcode
            generate_barcode_and_save(product_barcode, product_name)
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

class PrintBarcode(LoginRequiredMixin, View):
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
            barcode_filename = f"barcode_{product_name}.png"
            try:
               print(f'Printing barcode for {product_name}')
               print_barcode(barcode_filename, product_name)
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
          else:
            user_search_input = form.cleaned_data['search_field']
            if user_search_input:
              self.items = Product.objects.filter(**{f"{selectedOption}__contains": user_search_input})
            else:   # If search field is empty, show all products
              self.items = Product.objects.order_by('title')
        else:
          form = SearchForm1()
      return render(request, 'Dashboard/print-barcode.html', {'items': self.items, 'form': form})


class CreateQRCode(LoginRequiredMixin, View):
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

class ProductFinder(LoginRequiredMixin, View):
   def get(self, request):
      return redirect(request, 'Dashboard/scan_barcode.html')
   def post(self, request):
      barcode2 = request.POST.get('scannedData', '')
      try:
        product = Product.objects.get(barcode=int(barcode2))
      except Product.DoesNotExist:
          error = "Product does not exist."
          return render(request, 'Dashboard/scan_barcode.html', {'error': error})
      except ValueError:
         error = "The value received is of incorrect type."
         return render(request, 'Dashboard/scan_barcode.html', {'error': error}) 
      return render(request, 'Dashboard/quantity-adjuster.html', {'product': product})

 

   