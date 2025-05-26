from typing import Any
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, View
from django.urls import reverse_lazy
from Pages.form import ProductForm, ProductForm2, SearchForm1
import logging
from utils.print_barcode import print_barcode
from utils.generate_barcode import generate_barcode_and_save
from django.contrib import messages
from django.db.models import F
from django.core.mail import send_mail
from datetime import datetime
from EORLogging.models import LogEntry

logger = logging.getLogger('main')

class AddProduct(UserPassesTestMixin,View):
    
    template_name = 'product/product_form.html'
    success_url = 'inventory'  # Update with the appropriate URL

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
       return redirect('home')

    def get(self, request, *args, **kwargs):
        form = ProductForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = ProductForm(request.POST, user=request.user)
        print_b = bool(request.POST.get('printBarcode', False))
        if form.is_valid():
            form.instance.user = request.user
            product = form.save()
            product_name = product.title
            product_location = product.location_ID
            product_part = product.product_ID
            product_barcode = product.barcode
            generate_barcode_and_save(product_barcode, product_name, product_part, product_location)
            if print_b:
                print_barcode(product_name)
                product.printed = True
                product.save()
            # Log information
            # logID = getattr(request.user, 'username', 'Unknown User')
            # logProduct = form.cleaned_data['title']
            # logQuantity = form.cleaned_data['quantity']
            # logger.info(f'User {logID} added a product: {logProduct} (Quantity: {logQuantity})')

            return redirect(self.success_url)

        return render(request, self.template_name, {'form': form})
  

class EditProduct(UserPassesTestMixin, View):
    template_name = 'product/product_form.html'
    success_url = reverse_lazy('inventory') 
  

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
       return redirect('home')

    def get(self, request, *args, **kwargs):
        product = Product.objects.get(pk=kwargs['pk'])
        if request.user.groups.filter(name='Inventory Technician').exists():
           form2 = ProductForm2(instance=product)
        elif request.user.is_superuser:
           form1 = ProductForm(instance=product, user=request.user)      
        if request.user.groups.filter(name='Inventory Technician').exists():
          return render(request, self.template_name, {'form': form2})
        elif request.user.is_superuser:
          return render(request, self.template_name, {'form': form1})

    def post(self, request, *args, **kwargs):
        product = Product.objects.get(pk=kwargs['pk'])
        if request.user.groups.filter(name='Inventory Technician').exists():
            form = ProductForm2(request.POST, instance=product)
        elif request.user.is_superuser:
            form = ProductForm(request.POST, instance=product, user=request.user)
        if form.is_valid():
         
            if request.user.is_superuser:
              # Compare the new values with the original values
              if (request.session.get('originalProduct', '') != form.cleaned_data['title'] or
                  request.session.get('originalLocation', '') != form.cleaned_data['location_ID'] or
                  request.session.get('originalProductID', '') != form.cleaned_data['product_ID']):
                  product.printed = False
            else:
               if (request.session.get('originalLocation', '') != form.cleaned_data['location_ID']):
                  product.printed = False
            product.modified_by = request.user
            product = form.save()
            product_name = product.title
            product_location = product.location_ID
            product_part = product.product_ID
            product_barcode = product.barcode
            generate_barcode_and_save(product_barcode, product_name, product_part, product_location)
            if request.POST.get('printBarcode', False):
                print_barcode(product_name)
                product.printed = True
                product.save()
            return redirect(self.success_url)
        return render(request, self.template_name, {'form': form})




class AddBarcodeHub(UserPassesTestMixin, View):
    template_name = 'product/product_barcode_finder.html'
    items = None

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
       return redirect('home')

    def get(self, request):
      form = SearchForm1()
      # self.items = Product.objects.order_by('title')
      return render(request, self.template_name, {'items':self.items, 'form': form})

    def post(self, request):
      if request.method == 'POST':
        form = SearchForm1(request.POST)
        if form.is_valid():
          selectedOption = form.cleaned_data['inventory_field']
          if selectedOption == 'Show All':
            self.items = Product.objects.order_by('title')
            # return render(request, 'product/product_barcode_finder.html', {'items': self.items, 'form': form})
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
      return render(request, 'product/product_barcode_finder.html', {'items': self.items, 'form': form, })
    

class AddBarcode(UserPassesTestMixin, View):
    template_name = 'product/append_barcode.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
       return redirect('home')

    def get(self, request, pk):
        product = Product.objects.get(pk=pk)
        return render(request, self.template_name, {'product': product})

    def post(self, request, pk):
        try:
            barcode = request.POST.get('barcode')
            product = Product.objects.get(pk=pk)
            product.manufacturer_barcode = barcode
            product_title= product.title
            product.modified_by = request.user
            product.save()
            messages.success(request, f'Barcode {barcode} added successfully to {product_title}.')
            return redirect('barcode-hub')
        except Exception as e:
            messages.error(request, 'Failed to add barcode: {}'.format(e))
            return redirect('barcode-hub')
         

class DeleteProduct(UserPassesTestMixin, View):
    template_name = 'product/delete_product.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
       return redirect('home')


    def get(self, request, pk):
        item = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'item': item})

    def post(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            logProduct = product.title
            # logQuantity = product.quantity

            # logger.info(
            #     f'User {request.user.username} deleted {logProduct} with quantity: {logQuantity}  '
            # )

            product.delete()
            # Log the deletion
            details = f"Product {product.title} was deleted by {request.user}"
            LogEntry.objects.create(
            user=request.user,
            action_category='DELETE',
            details=details,
            product_name=product.title
        )
            messages.success(request, f'Successfully deleted {logProduct}!')
        except Exception as e:
            messages.error(request, f'Error during delete: {e}')

        return redirect('inventory')

class update_quantity(UserPassesTestMixin, View):
   
   def test_func(self):
        return self.request.user.is_staff
    
   def handle_no_permission(self):
       return redirect('home')

   def get(self, request):
      return render(request, 'Dashboard/scan_barcode.html')
   def post(self, request):
      if request.method == "POST":
        quantity_value = int(request.POST.get('integerDisplay', 0))
        product_ID = request.POST.get('product_id', None)
        text = request.POST.get('textInput', "No message given")
        try:
          product = Product.objects.get(id=product_ID)
        except Product.DoesNotExist as e:
            render(request, "error.html", {'error': e})
        except:
            e = "Unknown error"
            render(request, "error.html", {"error":e})
        product_name = product.title
        product_older_quantity = product.quantity
        # product.quantity = F("quantity") + quantity_value
        product.quantity += quantity_value
        # alter the user who modified the product
        product.modified_by = request.user
        product.save()
        product.refresh_from_db()
        # grab the current date and time
        date_and_time = datetime.now()
        date_string = date_and_time.strftime("%m/%d/%Y, %H:%M:%S")
        if product.quantity < 0:
          try:
            send_mail(
                f"Negative Quantity for {product_name}",
                f"Product {product_name} has a negative quantity of {product.quantity} by {request.user.username} on {date_string}\nThe original quantity was {product_older_quantity}.\nReason: {text}",
                "MCSinventory@django.com",
                ["kenny@marinecustomsolutions.com"],
                fail_silently=True,
                )
          except Exception as e:
            print(f"Error sending email: {e}")
        elif product.high_priority == True:
            try:
              send_mail(
                  f"H.P. {product_name} Quantity Updated",
                  f"Product {product_name} has been updated by {request.user.username} from {product_older_quantity} to {product.quantity} on {date_string}\nReason: {text}",
                  "MCSinventory@django.com",
                  ["kenny@marinecustomsolutions.com"],
                  fail_silently=True,
              )
            except Exception as e:
              print(f"Error sending email: {e}")

        # product_new_quantity = product.quantity
        # logger.info(
        #           f"User {request.user.username} alterred {product_name}'s quantity from : {product_older_quantity} to {product_new_quantity}\nReason: {text}"
        #       )
        return redirect("detect_barcodes")


    
