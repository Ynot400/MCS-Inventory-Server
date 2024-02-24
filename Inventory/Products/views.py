from typing import Any
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, View
from django.urls import reverse_lazy
from Pages.form import ProductForm, ProductForm2
import logging
from django.contrib import messages
from django.db.models import F
from django.core.mail import send_mail
from datetime import datetime

logger = logging.getLogger('main')

class AddProduct(LoginRequiredMixin,View):
    template_name = 'product/product_form.html'
    success_url = 'inventory'  # Update with the appropriate URL

    def get(self, request, *args, **kwargs):
        form = ProductForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = ProductForm(request.POST, user=request.user)
        if form.is_valid():
            form.instance.user = request.user
            form.save()

            # Log information
            logID = getattr(request.user, 'username', 'Unknown User')
            logProduct = form.cleaned_data['title']
            logQuantity = form.cleaned_data['quantity']
            logger.info(f'User {logID} added a product: {logProduct} (Quantity: {logQuantity})')

            return redirect(self.success_url)

        return render(request, self.template_name, {'form': form})
  

class EditProduct(LoginRequiredMixin, View):
    template_name = 'product/product_form.html'
    success_url = reverse_lazy('inventory') 
    logID = None
    originalProduct = ""
    originalQuantity = 0
    originalLocation = ""
    originalProductID = ""
    originalMarketPrice = 0.0
    originalOurPrice = 0.0
        
    def get(self, request, *args, **kwargs):
        product = Product.objects.get(pk=kwargs['pk'])
        if request.user.groups.filter(name='Inventory Technician').exists():
           form2 = ProductForm2(instance=product)
        elif request.user.is_superuser:
           form1 = ProductForm(instance=product, user=request.user)
        request.session['originalProduct'] = product.title
        request.session['originalQuantity'] = int(product.quantity)
        request.session['originalLocation'] = product.location_ID
        request.session['originalProductID'] = product.product_ID

        if request.user.is_superuser:
          request.session['originalMarketPrice'] = float(product.admin_field_price1)
          request.session['originalOurPrice'] = float(product.admin_field_price2)

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
            form.save()


            self.logID = getattr(request.user, 'username', 'Unknown User')
            self.originalProduct = request.session.get('originalProduct', '')
            self.originalQuantity = request.session.get('originalQuantity', 0)
            self.originalLocation = request.session.get('originalLocation', '')
            self.originalProductID = request.session.get('originalProductID', '')
            self.originalMarketPrice = request.session.get('originalMarketPrice', 0.0)
            self.originalOurPrice = request.session.get('originalOurPrice', 0.0)
            if request.user.groups.filter(name='Inventory Technician').exists():
                logger.info(
                    f'Inventory Technician {self.logID} edited a product:\n'
                    f'Original: {self.originalProduct} - Quantity: {self.originalQuantity} - Location: {self.originalLocation} - Part Number: {self.originalProductID}\n'
                    f"Updated: {form.cleaned_data['location_ID']} - {form.cleaned_data['description']}"
                
                )
            elif(self.request.user.is_superuser):
          
        
              logger.info(
                  f'User {self.logID} edited a product:\n'
                  f"Original: {self.originalProduct} - Quantity: {self.originalQuantity} - Location: {self.originalLocation} - Part Number: {self.originalProductID} - Retail: {self.originalMarketPrice} - Cost: {self.originalOurPrice}\n"
                  f"Updated: {form.cleaned_data['title']} - Quantity: {form.cleaned_data['quantity']} - Location: {form.cleaned_data['location_ID']} - Part Number: {form.cleaned_data['product_ID']} - Retail: {form.cleaned_data['admin_field_price1']} - Cost: {form.cleaned_data['admin_field_price2']}"
              )
            else:
              logger.info(
                f'User {self.logID} edited a product:\n'
                f'Original: {self.originalProduct} - Quantity: {self.originalQuantity} - Location: {self.originalLocation} - Part Number: {self.originalProductID}\n'
                f"Updated: {form.cleaned_data['title']} - Quantity: {form.cleaned_data['quantity']} - Location: {form.cleaned_data['location_ID']} - Part Number: {form.cleaned_data['product_ID']}"
            )
                

            return redirect(self.success_url)

        return render(request, self.template_name, {'form': form})

class DeleteProduct(LoginRequiredMixin, View):
    template_name = 'product/delete_product.html'

    def get(self, request, pk):
        item = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'item': item})

    def post(self, request, pk):
        try:
            product = get_object_or_404(Product, pk=pk)
            logProduct = product.title
            logQuantity = product.quantity

            logger.info(
                f'User {request.user.username} deleted {logProduct} with quantity: {logQuantity}  '
            )

            product.delete()
            messages.success(request, f'Successfully deleted {logProduct}!')
        except Exception as e:
            messages.error(request, f'Error during delete: {e}')

        return redirect('inventory')

def update_quantity(request):
   if request.method == "POST":
      quantity_value = int(request.POST.get('integerDisplay', 0))
      product_ID = request.POST.get('product_id', None)
      try:
        product = Product.objects.get(id=product_ID)
      except Product.DoesNotExist as e:
         render(request, "error.html", {'error': e})
      except:
         e = "Unknown error"
         render(request, "error.html", {"error":e})
      product_name = product.title
      product_older_quantity = product.quantity
      product.quantity = F("quantity") + quantity_value
      product.save()
      product.refresh_from_db()
      if product.quantity < 0:
        product.quantity = 0
        product.save()
        product.refresh_from_db()
      if product.high_priority == True:
         date_and_time = datetime.now()
         date_string = date_and_time.strftime("%m/%d/%Y, %H:%M:%S")
         try:
            send_mail(
                f"H.P. {product_name} Quantity Updated",
                f"Product {product_name} has been updated by {request.user.username} from {product_older_quantity} to {product.quantity} on {date_string}",
                "MCSinventory@django.com",
                ["jluke01@outlook.com"],
                fail_silently=False,
            )
         except Exception as e:
            print(f"Error sending email: {e}")

      product_new_quantity = product.quantity
      logger.info(
                f"User {request.user.username} alterred {product_name}'s quantity from : {product_older_quantity} to {product_new_quantity}"
            )
      return render(request, "Dashboard/scan_barcode.html")


    
