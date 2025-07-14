
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import View
from Pages.form import SearchForm1
from Products.models import Product
from utils.generate_barcode import generate_barcode_and_save
from utils.generate_qrcode import generateQR
from utils.print_barcode import print_barcode
import re
from utils.tokens import create_submission_token
from django.contrib import messages
from utils.searchFormProductFilter import filter_products
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from jobtickets.models import JobTicket
from django.utils import timezone
from datetime import timedelta


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
    template_name = 'Dashboard/print-barcode.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')
    
    def get(self, request):
        form = SearchForm1(request.GET or None)
        items = None
        paginated_items = None

        if form.is_valid() and any(form.cleaned_data.values()):
            print("Form is valid, filtering products")
            items = filter_products(form)

            paginator = Paginator(items, 25)
            page = request.GET.get('page')

            try:
                paginated_items = paginator.page(page)
            except PageNotAnInteger:
                paginated_items = paginator.page(1)
            except EmptyPage:
                paginated_items = paginator.page(paginator.num_pages)

        return render(request, self.template_name, {
            'form': form,
            'items': paginated_items,
            'printAll': False
        })


    def post(self, request):
        # Handle AJAX barcode printing
        if 'printBarcode' in request.POST:
            id = request.POST.get('id')
            try:
                product = Product.objects.get(pk=id)
                # print(f'Printing barcode for {product.title}')
                print_barcode(product.title, product.product_ID, product.location_ID, product.vendor)
                product.printed = True
                product.save()
                return JsonResponse({'status': 'success'})
            except Product.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Product not found'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Error printing barcode: {str(e)}'})

       

        #  Check for "Not Yet Printed" manually via POST flag
        if request.POST.get('printed') == 'true':
            items = Product.objects.filter(printed=False).order_by('title')
            return render(request, self.template_name, {
            'form': SearchForm1(),
            'items': items,
            'printAll': True
                })
    

        # If no specific action, redirect to print-barcode
        return redirect('print-barcode')


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
        barcode_input = request.POST.get('scannedData', '').strip()
        # print(f"Scanned barcode: {barcode_input}")
  
        # General validation
        if len(barcode_input) > 64:
            messages.error(request, "Barcode is too long to be valid.")
            return redirect('barcode-quantity')

        if not re.match(r'^[\w\-]+$', barcode_input): # this regex will accept any barcode that contains alphanumeric characters, underscores, or hyphens -- anything else will be considered invalid
            messages.error(request, "Invalid characters in barcode.")
            return redirect('barcode-quantity')

        # First: try to find product using manufacturer_barcode (alphanumeric allowed)
        try:
            product = Product.objects.get(manufacturer_barcode=barcode_input)
            # Generate the submission token and store it in the session
            return self._render_quantity_adjuster(request, product)
        except Product.DoesNotExist:
            pass  # Fall back to internal barcode

        # If not found, try parsing internal barcode (must be numeric)
        if barcode_input.isdigit():
            try:
                internal_barcode = int(barcode_input) // 10
                product = Product.objects.get(barcode=internal_barcode)
                # Generate the submission token and store it in the session
                return self._render_quantity_adjuster(request, product)
            except Product.DoesNotExist:
                pass
            except ValueError:
                # This should never hit if isdigit() passed, but keep just in case
                messages.error(request, "Internal barcode is not a valid number.")
                return redirect('barcode-quantity')
        # If no product found, return an error message
        messages.error(request, "Product does not exist or barcode is invalid.")
        return redirect('barcode-quantity')
    
    def _render_quantity_adjuster(self, request, product):
        """Render the quantity adjuster with job ticket integration"""
        token = create_submission_token()
        job_tickets = JobTicket.objects.filter( status='InProgress',
                                                created_at__gte=timezone.now() - timedelta(days=100)  # Extended time window
                                                ).order_by('customer_name')

        return render(request, 'Dashboard/quantity-adjuster.html', {
            'product': product,
            'submission_token': token,
            'job_tickets': job_tickets,
        })



class ProductFinderManufacturer(UserPassesTestMixin, View):
  def test_func(self):
      return self.request.user.is_staff
  def handle_no_permission(self):
      return redirect('home')
  def get(self, request):
      return render(request, 'product/manufacturer_scanning.html')
  def post(self, request):
    barcode_input = request.POST.get('scannedData', '').strip()
    # print(f"Scanned barcode: {barcode_input}")
   
    # General validation
    if len(barcode_input) > 64:
        messages.error(request, "Barcode is too long to be valid.")
        return redirect('manufacturer-scan')

    if not re.match(r'^[\w\-]+$', barcode_input): # this regex will accept any barcode that contains alphanumeric characters, underscores, or hyphens -- anything else will be considered invalid
        messages.error(request, "Invalid characters in barcode.")
        return redirect('manufacturer-scan')

    # First: try to find product using manufacturer_barcode (alphanumeric allowed)
    try:
        product = Product.objects.get(manufacturer_barcode=barcode_input)
        return redirect('add-barcode', pk=product.pk)

    except Product.DoesNotExist:
        pass  # Fall back to internal barcode

    # If not found, try parsing internal barcode (must be numeric)
    if barcode_input.isdigit():
        try:
            internal_barcode = int(barcode_input) // 10
            product = Product.objects.get(barcode=internal_barcode)
            return redirect('add-barcode', pk=product.pk)

        except Product.DoesNotExist:
            pass
        except ValueError:
            # This should never hit if isdigit() passed, but keep just in case
            messages.error(request, "Internal barcode is not a valid number.")
            return redirect('manufacturer-scan')
    # If no product found, return an error message
    messages.error(request, "Product does not exist or barcode is invalid.")
    return redirect('manufacturer-scan')
   