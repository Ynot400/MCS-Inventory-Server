from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Product(models.Model):
    title = models.CharField(max_length=200)
    # location_ID = models.CharField(max_length=11, unique=True)

    # The location ID will now be composed of:
    # Section (2 characters 0A, 0B, ..., ZY, ZZ)
    # Level (2 characters 0A, 0B, ..., ZY, ZZ)
    # Vertical (2 characters 00, 01, ..., 99)
    # Horizontal (2 characters 00, 01, ..., 99)
    # A location ID might look like: "0A-0B-00-00" or "AZ-0Z-99-99"
    # A location ID may either pertain to a cubby or a shelf.
    # A cubby will require the vertical and horizontal fields to be filled in and unique.
    # A shelf will not require the vertical and horizontal fields to be filled in. 
    section = models.CharField(max_length=2)
    level = models.CharField(max_length=2)
    vertical = models.CharField(max_length=2, blank=True, null=True)
    horizontal = models.CharField(max_length=2, blank=True, null=True)
    # Is structured will determine if the product is on a shelf or in a cubby. 
    is_structured = models.BooleanField(default=True)


    product_ID = models.CharField(max_length=191, unique=True, blank=True, null=True) # Part Number

    quantity = models.PositiveIntegerField()
    min_quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    max_quantity = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])



    vendor = models.CharField(max_length=200, blank=True, null=True, default=None)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True) 
    barcode = models.BigIntegerField(unique=True, blank=True, null=True)
    manufacturer_barcode = models.CharField(max_length=64, unique=True, null=True, blank=True)
    high_priority = models.BooleanField(default=False)
    description = models.CharField(max_length=1000, null=True, blank=True, default='')
    printed = models.BooleanField(default=False)
    # modified_by = models.ForeignKey(User, default=None, on_delete=models.SET_NULL, null=True, related_name='modified_by')

    def is_below_min(self): # Checks if the quantity is below the minimum threshold
        return self.quantity < self.min_quantity

    def is_above_max(self): # Checks if the quantity is above the maximum threshold
        return self.quantity > self.max_quantity


    admin_field_price1 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )

    admin_field_price2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )

    def save(self, *args, **kwargs):

        if self.admin_field_price1 is None:
            self.admin_field_price1 = 0.00
        if self.admin_field_price2 is None:
            self.admin_field_price2 = 0.00
        super(Product, self).save(*args, **kwargs)


    def clean(self):
        super().clean()

        # Skip model-level checks if required fields are missing (because the form is already invalid)
        if self.is_structured and (not self.vertical or not self.horizontal):
            # Avoid duplicate errors if form already rejected
            return

        if self.is_structured:
            conflict = Product.objects.filter(
                section=self.section,
                level=self.level,
                vertical=self.vertical,
                horizontal=self.horizontal,
                is_structured=True
            )
            if self.pk:
                conflict = conflict.exclude(pk=self.pk)
            if conflict.exists():
                raise ValidationError("This cubby location is already in use.")

    @property
    def admin_field_1(self):
        if self.user.is_superuser:
            return self.admin_field_price1
        return None

    @property
    def admin_field_2(self):
        if self.user.is_superuser:
            return self.admin_field_price2
        return None

    # when location_ID is called, it will return the location ID in the format "section-level-vertical-horizontal"
    @property
    def location_ID(self):
        return f"{self.section}-{self.level}-{self.vertical or 'XX'}-{self.horizontal or 'XX'}"


    def __str__(self):
        return self.title

@receiver(pre_save, sender=Product)
def generate_barcode(sender, instance, **kwargs):
    if not instance.barcode:
        while True: # even though a barcode matching another is astronomically unlikely, we still want to ensure uniqueness 
            random_barcode = random.randint(10**11, 10**12 - 1)
            if not Product.objects.filter(barcode=random_barcode).exists():
                instance.barcode = random_barcode
                break
