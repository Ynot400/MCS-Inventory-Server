from django.db import models
from django.contrib.auth.models import User
import random
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Product(models.Model):
    title = models.TextField(max_length=200)
    location_ID = models.TextField(max_length=20)
    product_ID = models.TextField()
    quantity = models.IntegerField()
    vendor = models.TextField(max_length=200, default=None)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True)
    barcode = models.BigIntegerField(unique=True, blank=True, null=True)
    manufacturer_barcode = models.CharField(max_length=64, unique=True, null=True, blank=True)
    high_priority = models.BooleanField(default=False)
    description = models.TextField(max_length=150, default='')
    printed = models.BooleanField(default=False)
    modified_by = models.ForeignKey(User, default=None, on_delete=models.SET_NULL, null=True, related_name='modified_by')



    admin_field_price1 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=True, default=0.00)
    admin_field_price2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=True, default=0.00)

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
        # Generate a random 12-digit integer
        instance.barcode = random.randint(10**11, 10**12 - 1)
