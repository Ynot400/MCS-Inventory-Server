from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import View
from django.urls import reverse_lazy
from Pages.form import ProductForm, ProductForm2, SearchForm1
from utils.print_barcode import print_barcode
from utils.generate_barcode import generate_barcode_and_save
from django.contrib import messages
from django.core.mail import send_mail
from datetime import datetime
import re
from django.db import transaction, IntegrityError
from Pages.models import SubmissionToken
from utils.tokens import create_submission_token
from utils.log_generator import log_product_action
from decimal import Decimal
from utils.searchFormProductFilter import filter_products
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging



logger = logging.getLogger('server')

class AddProduct(UserPassesTestMixin, View):
    template_name = 'product/product_form.html'
    success_url = 'inventory'  # Update with the appropriate URL

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, *args, **kwargs):
        form = ProductForm(user=request.user)
        token = create_submission_token()
        return render(request, self.template_name, {'form': form, 'submission_token': token, 'vendor_list': form.vendor_datalist})
    
    def post(self, request, *args, **kwargs):
        # used to fix the decimal issue with json
        def serialize_value(val):
            if isinstance(val, Decimal):
                return float(val)
            return val
        
        form = ProductForm(request.POST, user=request.user)

        # === Submission Token Check ===
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            # print("Missing submission token.")
            return redirect("inventory")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            # print("Invalid or already used submission token.")
            return redirect("inventory")

       
        if form.is_valid():
            manufacturer_barcode = None

            if isinstance(manufacturer_barcode, str): # check if there is a manufacturer_barcode
                manufacturer_barcode = form.cleaned_data.get('manufacturer_barcode', '').strip()
    

            if manufacturer_barcode:
                if len(manufacturer_barcode) > 64:
                    form.add_error('manufacturer_barcode', "Barcode exceeds maximum allowed length.")
                elif not re.match(r'^[\w\-]+$', manufacturer_barcode):
                    form.add_error('manufacturer_barcode', "Barcode contains invalid characters.")
                elif Product.objects.filter(manufacturer_barcode=manufacturer_barcode).exists():
                    form.add_error('manufacturer_barcode', "This barcode is already assigned to another product.")

            if form.errors:
                return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})

            try:
                # print(f"This will be only printed once for the product: {form.cleaned_data['title']}")
                with transaction.atomic():
                    product = form.save()
                    
                    # === LOG ENTRY CREATED HERE ===
                    log_product_action(
                        user=request.user,
                        action_category="CREATE",
                        product=product,
                        changes={
                            'Product Name': product.title,
                            'Location ID': product.location_ID,
                            'Part Number': product.product_ID,
                            'Starting Quantity': product.quantity,
                            'Vendor': product.vendor,
                            'Description': product.description,
                            'Retail': serialize_value(product.admin_field_price1),
                            'Cost': serialize_value(product.admin_field_price2),
                            'Manufacturer Barcode': product.manufacturer_barcode,
                            'High Priority': product.high_priority,
                            'Min Quantity': product.min_quantity,
                            'Max Quantity': product.max_quantity
                        }
                    )


                # Only delete token **after** save succeeded
                SubmissionToken.objects.filter(token=token_from_form).delete()

                # barcode generation
                generate_barcode_and_save(
                    product.barcode,
                    product.title,
                    product.product_ID,
                    product.location_ID,
                    product.vendor
                )

                if request.POST.get('printBarcode'):
                    print_barcode(product.title, product.product_ID, product.location_ID, product.vendor)
                    product.printed = True
                    product.save()

                return redirect(self.success_url)

            except IntegrityError as e:
                form.add_error(None, f"A problem occurred while saving. One or more fields may already exist in another product. Please check for duplicates and try again. {e}")
                return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})
        else:
            # print("Form is not valid:", form.errors)
            return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})


class EditProduct(UserPassesTestMixin, View):
    template_name = 'product/product_form.html'
    success_url = reverse_lazy('inventory')

 
    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get_form(self, request, product):
        if request.user.is_superuser:
            return ProductForm(instance=product, user=request.user)
        elif request.user.groups.filter(name='Inventory Technician').exists():
            return ProductForm2(instance=product)
        return None

    def get(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=kwargs['pk'])
        form = self.get_form(request, product)
        token = create_submission_token()
        if not form:
            return redirect('home')
        
        # Store original values in session
        request.session['originalProduct'] = product.title
        request.session['originalLocation'] = product.location_ID
        request.session['originalProductID'] = product.product_ID

        # Check if the form has a vendor datalist
        vendor_list = form.vendor_datalist if hasattr(form, 'vendor_datalist') else None

        return render(request, self.template_name, {'form': form, 'submission_token': token, 'vendor_list': vendor_list})

    def post(self, request, *args, **kwargs):

        tracked_fields = {
            'title':'Product Name', 
            'location_ID':'Location ID', 
            'product_ID':'Part Number', 
            'quantity':'Quantity',
            'min_quantity':'Min Quantity',
            'max_quantity':'Max Quantity', 
            'vendor':'Vendor',
            'description':'Description',
            'admin_field_price1':'Retail', 
            'admin_field_price2':'Cost',
            'manufacturer_barcode':'Manufacturer Barcode', 
            'barcode':'Barcode', 
            'high_priority':'High Priority'
        }

        # used to fix the decimal issue with json
        def serialize_value(val):
            if isinstance(val, Decimal):
                return float(val)
            return val
        

        product = get_object_or_404(Product, pk=kwargs['pk'])
        form = (ProductForm(request.POST, instance=product, user=request.user)
                if request.user.is_superuser else
                ProductForm2(request.POST, instance=product))

        print_b = bool(request.POST.get('printBarcode', False))

        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            # print("Missing submission token.")
            return redirect("inventory")

        token_exists = SubmissionToken.objects.filter(token=token_from_form).exists()
        if not token_exists:
            # print("Invalid or already used submission token.")
            return redirect("inventory")
       

        if form.is_valid():

            manufacturer_barcode = None

            if isinstance(manufacturer_barcode, str):
                manufacturer_barcode = form.cleaned_data.get('manufacturer_barcode', '').strip()
    

            # Barcode validation
            if manufacturer_barcode:
                if len(manufacturer_barcode) > 64:
                    form.add_error('manufacturer_barcode', "Barcode exceeds maximum allowed length.")
                elif not re.match(r'^[\w\-]+$', manufacturer_barcode):
                    form.add_error('manufacturer_barcode', "Barcode contains invalid characters.")
                elif Product.objects.filter(manufacturer_barcode=manufacturer_barcode).exclude(pk=product.pk).exists():
                    form.add_error('manufacturer_barcode', "This barcode is already assigned to another product.")
        
            if form.errors:
                return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})
            

            try:
                with transaction.atomic():
                    # Compare session-stored values to determine if printed should be reset
                    if not request.user.groups.filter(name='Inventory Technician').exists() and request.user.is_superuser:
                        title_changed = request.session.get('originalProduct') != form.cleaned_data['title']
                        id_changed = request.session.get('originalProductID') != form.cleaned_data['product_ID']

                    form_location_id = f"{form.cleaned_data['section']}-{form.cleaned_data['level']}-{form.cleaned_data['vertical'] or 'XX'}-{form.cleaned_data['horizontal'] or 'XX'}"
                    loc_changed = request.session.get('originalLocation') != form_location_id

                                        

                    # resets the printed status
                    if request.user.is_superuser:
                        if title_changed or loc_changed or id_changed:
                            # print("Changes detected, resetting printed status.")
                            product.printed = False
                    else:
                        if loc_changed:
                            product.printed = False
                    
                    # Create log entry before saving

                    newProduct = form.save(commit=False)
                    oldProduct = Product.objects.get(pk=product.pk)

                    changes = {}
                 
                


                    for field in tracked_fields:
                        if field == 'location_ID':
                            oldVal = oldProduct.location_ID
                            newVal = product.location_ID
                        else:
                            oldVal = getattr(oldProduct, field)
                            newVal = getattr(product, field)
                        if oldVal != newVal:
                            fieldName = tracked_fields.get(field, field)  # fallback to raw field name if not labeled
                            changes[fieldName] = {
                                'old_value': serialize_value(oldVal),
                                'new_value': serialize_value(newVal)
                            }
                    
                    newProduct.save() # actyally save the product
                    
                    # if the save was succesful, log the new entry
                    if changes:
                        log_product_action(
                                user=request.user,
                                action_category="UPDATE",
                                product=product,
                                changes=changes
                            )
                    
                    # Session values are no longer needed
                    request.session.pop('originalProduct', None)
                    request.session.pop('originalLocation', None)
                    request.session.pop('originalProductID', None)

                    
                # Only delete token **after** save succeeded
                SubmissionToken.objects.filter(token=token_from_form).delete()

                # generate a new barcode if value changes
                if request.user.is_superuser:
                    if title_changed or loc_changed or id_changed:
                         generate_barcode_and_save(
                            product.barcode,
                            product.title,
                            product.product_ID,
                            product.location_ID,
                            product.vendor
                        )
                else:
                    if loc_changed:
                        generate_barcode_and_save(
                            product.barcode,
                            product.title,
                            product.product_ID,
                            product.location_ID,
                            product.vendor
                        )

                if print_b:
                    print_barcode(product.title, product.product_ID, product.location_ID, product.vendor)
                    product.printed = True
                    product.save()

                return redirect(self.success_url)

            except IntegrityError as e:
                form.add_error(None, "A problem occurred while saving. One or more fields may already exist in another product. Please check for duplicates and try again.")
                return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})

        return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})

class AddBarcodeHub(UserPassesTestMixin, View):
    template_name = 'product/product_barcode_finder.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        form = SearchForm1(request.GET or None)
        items = None
        paginated_items = None

        if form.is_valid() and any(form.cleaned_data.values()):
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
        })

    
class AddBarcode(UserPassesTestMixin, View):
    template_name = 'product/append_barcode.html'

    def test_func(self):
        return self.request.user.groups.filter(name='Inventory Technician').exists() or self.request.user.is_superuser
    
    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'product': product})

    def post(self, request, pk):
        barcode = request.POST.get('barcode', '').strip()
        product = get_object_or_404(Product, pk=pk)

        # Validate: not empty
        if not barcode:
            messages.error(request, "Barcode cannot be empty.")
            return render(request, self.template_name, {'product': product})

        # Validate: max length
        if len(barcode) > 64:
            messages.error(request, "Barcode exceeds maximum allowed length.")
            return render(request, self.template_name, {'product': product})

        # Validate: allowed characters (letters, digits, underscores, hyphens only)
        if not re.match(r'^[\w\-]+$', barcode):
            messages.error(request, "Barcode contains invalid characters.")
            return render(request, self.template_name, {'product': product})

        # Check for duplicates
        if Product.objects.filter(manufacturer_barcode=barcode).exclude(pk=pk).exists():
            messages.error(request, f"Barcode {barcode} is already assigned to another product.")
            return render(request, self.template_name, {'product': product})

        # Save and log
        old_barcode = product.manufacturer_barcode
        product.manufacturer_barcode = barcode
        product.save()

        # Log the action
        log_product_action(
            user=request.user,
            action_category='UPDATE',
            product=product,
            summary=f"Manufacturer barcode update",
            changes={
                'manufacturer_barcode': {
                    'old_value': old_barcode,
                    'new_value': barcode
                }
            }
        )

        messages.success(request, f'Barcode {barcode} added successfully to {product.title}.')
        return redirect('barcode-hub')
    
class DeleteProduct(UserPassesTestMixin, View):
    template_name = 'product/delete_product.html'

    def test_func(self):
        return (
            self.request.user.groups.filter(name='Inventory Technician').exists() or
            self.request.user.is_superuser
        )

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request, pk):
        item = get_object_or_404(Product, pk=pk)
        return render(request, self.template_name, {'item': item})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product_title = product.title
        product_id = product.id
        product_barcode = product.barcode

        # Collect field values before deletion
        tracked_fields = {
            'title':'Product Name', 
            'location_ID':'Location ID', 
            'product_ID':'Part Number', 
            'quantity':'Quantity',
            'min_quantity':'Min Quantity',
            'max_quantity':'Max Quantity', 
            'vendor':'Vendor',
            'description':'Description',
            'admin_field_price1':'Retail', 
            'admin_field_price2':'Cost',
            'manufacturer_barcode':'Manufacturer Barcode', 
            'barcode':'Barcode', 
            'high_priority':'High Priority'
        }

        changes = {}
        for field in tracked_fields:
            val = getattr(product, field, None)
            if isinstance(val, Decimal):
                val = float(val)
            label = tracked_fields.get(field, field)  # fallback to raw field name if not labeled
            changes[label] = val

        try:
            # Log BEFORE delete
            log_product_action(
                user=request.user,
                action_category='DELETE',
                changes=changes,
                summary=f"{product_title} has been permanently deleted.",
            )

            product.delete()

            messages.success(request, f"Successfully deleted '{product_title}'.")
        except Exception as e:
            messages.error(request, f"Error deleting product: {e}")

        return redirect('inventory')


class update_quantity(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        return redirect('home')

    def get(self, request):
        return render(request, 'Dashboard/scan_barcode.html')

    @transaction.atomic
    def post(self, request):
        quantity_value = int(request.POST.get('integerDisplay', 0))
        product_ID = request.POST.get('product_id', None)
        text = request.POST.get('textInput', "No message given")

        # Token verification using the model
        token_from_form = request.POST.get('submission_token')
        if not token_from_form:
            # print("Missing submission token.")
            return redirect("detect_barcodes")

    
        # Lock the product row first
        try:
            # print(f"Attempting to lock product with ID {product_ID} for update")
            product = Product.objects.select_for_update().get(id=product_ID)
        except Product.DoesNotExist as e:
            return redirect("detect_barcodes")
        except Exception:
            return redirect("detect_barcodes")
        
        product_name = product.title
        product_older_quantity = product.quantity

        # Reject if resulting quantity would go negative
        if product_older_quantity + quantity_value < 0:
            messages.error(request, f"Cannot adjust quantity for by {quantity_value}. Resulting quantity would be negative.")
            return render(request, 'Dashboard/quantity-adjuster.html', {
                'product': product,
                'submission_token': token_from_form
            })
        elif quantity_value == 0:
            messages.error(request, "Submit a valid quantity change.")
            return render(request, 'Dashboard/quantity-adjuster.html', {
                'product': product,
                'submission_token': token_from_form
            })
        
        token_used = SubmissionToken.objects.filter(token=token_from_form).delete()
        if token_used[0] == 0:
            # print("Invalid or already used submission token.")
            return redirect("detect_barcodes")


        # print(f"Updating product {product.title} with quantity {quantity_value} by {request.user.username}")

        product_name = product.title
        product.quantity += quantity_value
        
        product.save()
        product.refresh_from_db()

        # Log the action
        log_product_action(
            user=request.user,
            action_category='UPDATE',
            product=product,
            summary=f"{text}",
            changes={
                'quantity': {
                    'old_value': product_older_quantity,
                    'new_value': product.quantity
                }
            }
        )

        # Email warnings
        if product.quantity <= 0:
            try:
                send_mail(
                    f"0 Quantity for {product_name}",
                    f"Product {product_name} has 0 quantity by {request.user.username} on {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}\nThe original quantity was {product_older_quantity}.\nReason: {text}",
                    "MCSinventory@django.com",
                    ["kenny@marinecustomsolutions.com"],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send 0 quantity warning email for '{product_name}': {e}")
        elif product.high_priority:
            try:
                send_mail(
                    f"H.P. {product_name} Quantity Updated",
                    f"Product {product_name} has been updated by {request.user.username} from {product_older_quantity} to {product.quantity} on {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}\nReason: {text}",
                    "MCSinventory@django.com",
                    ["kenny@marinecustomsolutions.com"],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error(f"Failed to send high-priority quantity update email for '{product_name}': {e}")

        return redirect("detect_barcodes")
