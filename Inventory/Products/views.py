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
from EORLogging.models import LogEntry
import re
from django.db import transaction, IntegrityError
from Pages.models import SubmissionToken
from utils.tokens import create_submission_token


# logger = logging.getLogger('main')

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
        return render(request, self.template_name, {'form': form, 'submission_token': token})
    
    def post(self, request, *args, **kwargs):
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
                    form.instance.modified_by = request.user
                    product = form.save()

                # Only delete token **after** save succeeded
                SubmissionToken.objects.filter(token=token_from_form).delete()

                # Optional barcode generation
                generate_barcode_and_save(
                    product.barcode,
                    product.title,
                    product.product_ID,
                    product.location_ID
                )

                if request.POST.get('printBarcode'):
                    # print_barcode(product.title)
                    product.printed = True
                    product.save()

                return redirect(self.success_url)

            except IntegrityError as e:
                form.add_error(None, f"A problem occurred while saving. One or more fields may already exist in another product. Please check for duplicates and try again. {e}")
                return render(request, self.template_name, {'form': form, 'submission_token': token_from_form})
        else:
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

        return render(request, self.template_name, {'form': form, 'submission_token': token})

    def post(self, request, *args, **kwargs):
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

                    loc_changed = request.session.get('originalLocation') != form.cleaned_data['location_ID']
                    


                    if request.user.is_superuser:
                        if title_changed or loc_changed or id_changed:
                            # print("Changes detected, resetting printed status.")
                            product.printed = False
                    else:
                        if loc_changed:
                            product.printed = False

                    product.modified_by = request.user
                    product = form.save()

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
                            product.location_ID
                        )
                else:
                    if loc_changed:
                        generate_barcode_and_save(
                            product.barcode,
                            product.title,
                            product.product_ID,
                            product.location_ID
                        )

                if print_b:
                    print_barcode(product.title)
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
        form = SearchForm1(initial={'show_all': True})
        items = Product.objects.order_by('title')  # Default display
        return render(request, self.template_name, {'form': form, 'items': items})

    def post(self, request):
        form = SearchForm1(request.POST)
        items = Product.objects.none()

        if form.is_valid():
            sort_order = form.cleaned_data.get('sort_order')

            if form.cleaned_data['show_all']:
                items = Product.objects.all()
            else:
                filters = {}
                if form.cleaned_data.get('product_name'):
                    filters['title__icontains'] = form.cleaned_data['product_name']
                if form.cleaned_data.get('product_ID'):
                    filters['product_ID__icontains'] = form.cleaned_data['product_ID']
                if form.cleaned_data.get('location_ID'):
                    filters['location_ID__icontains'] = form.cleaned_data['location_ID']
                if form.cleaned_data.get('vendor'):
                    filters['vendor__icontains'] = form.cleaned_data['vendor']
                    
                items = Product.objects.filter(**filters)

            if sort_order == 'recent':
                items = items.order_by('-date_created')
            elif sort_order == 'oldest':
                items = items.order_by('date_created')

        return render(request, self.template_name, {'form': form, 'items': items})
    
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
            return redirect('barcode-hub')

        # Validate: max length
        if len(barcode) > 64:
            messages.error(request, "Barcode exceeds maximum allowed length.")
            return redirect('barcode-hub')

        # Validate: allowed characters (letters, digits, underscores, hyphens only)
        if not re.match(r'^[\w\-]+$', barcode):
            messages.error(request, "Barcode contains invalid characters.")
            return redirect('barcode-hub')

        # Check for duplicates
        if Product.objects.filter(manufacturer_barcode=barcode).exclude(pk=pk).exists():
            messages.error(request, f"Barcode {barcode} is already assigned to another product.")
            return redirect('barcode-hub')

        # Apply and save
        product.manufacturer_barcode = barcode
        product.modified_by = request.user
        product.save()

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

        try:
            # Log BEFORE delete
            LogEntry.objects.create(
                user=request.user,
                action_category='DELETE',
                details=f"Product '{product_title}' (ID: {product_id}, barcode: {product_barcode}) was deleted by {request.user}.",
                product_name=product_title
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
            print("Missing submission token.")
            return redirect("detect_barcodes")

        token_used = SubmissionToken.objects.filter(token=token_from_form).delete()
        if token_used[0] == 0:
            print("Invalid or already used submission token.")
            return redirect("detect_barcodes")

        # Lock the product row first
        try:
            print(f"Attempting to lock product with ID {product_ID} for update")
            product = Product.objects.select_for_update().get(id=product_ID)
        except Product.DoesNotExist as e:
            return render(request, "error.html", {'error': e})
        except Exception:
            return render(request, "error.html", {"error": "Unknown error"})



        print(f"Updating product {product.title} with quantity {quantity_value} by {request.user.username}")

        product_name = product.title
        product_older_quantity = product.quantity
        product.quantity += quantity_value
        product.modified_by = request.user
        product.save()
        product.refresh_from_db()

        date_string = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        # Email warnings
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
        elif product.high_priority:
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

        return redirect("detect_barcodes")
