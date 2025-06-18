from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator

class Product(models.Model):
    title = models.CharField(max_length=200)
    location_ID = models.CharField(max_length=11, unique=True)
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
