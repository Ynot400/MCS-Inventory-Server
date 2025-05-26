from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from Products.models import Product

field_names = {
    'title': 'Product Name',
    'location_ID': 'Location ID',
    'product_ID': 'Part Number',
    'quantity': 'Quantity',
    'vendor': 'Vendor',
    'description': 'Description',
    'admin_field_price1': 'Retail Price',
    'admin_field_price2': 'Cost Price',
    'manufacturer_barcode': 'Manufacturer Barcode',
    'high_priority': 'High Priority',
}

class LogEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True, related_name='log_entries')
    action_category = models.CharField(max_length=10)  # 'CREATE', 'UPDATE', 'DELETE'
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField()
    product_name = models.CharField(max_length=50, blank=True, null=True)

@receiver(pre_save, sender=Product)
def log_product_action(sender, instance, **kwargs):
    if instance.pk is not None:
      old_instance = sender.objects.get(pk=instance.pk)
      changes = {}
      for field in instance._meta.fields:
          if field.name == 'printed':
            continue
          elif field.name == 'modified_by':
            continue
          if getattr(instance, field.attname) != getattr(old_instance, field.attname):
              changes[field.attname] = {
                  'old_value': getattr(old_instance, field.attname),
                  'new_value': getattr(instance, field.attname)
              }
      instance._changes_before_save = changes
      instance.prev_product_title = old_instance.title

@receiver(post_save, sender=Product)
def log_creation_adding_or_editing(sender, instance, created, **kwargs):
  # Your post-save logic here
  if created:
      details = (
        f"Product {instance.title} was created by {instance.user}\n"
        f"Part Number: {instance.product_ID}\n"
        f"Location ID: {instance.location_ID}\n"
        f"Quantity: {instance.quantity}\n"
        f"Vendor: {instance.vendor}\n"
        f"Description: {instance.description}"
    )
      LogEntry.objects.create(
          user=instance.user,
          action_category='CREATE',
          details=details,
          product_name=instance.title
      )
  else:
    if hasattr(instance, '_changes_before_save') and instance._changes_before_save:
      changes = instance._changes_before_save
      del instance._changes_before_save
      details = f'Product {instance.prev_product_title} was updated.\n'
      for field, values in changes.items():
            field_name = field_names.get(field, field)  # Use the user-friendly name if available, otherwise use the field name
            details += f'{field_name} was changed from {values["old_value"]} to {values["new_value"]}\n'
      LogEntry.objects.create(
          user=instance.modified_by,
          action_category='UPDATE',
          details=details,
          product_name=instance.prev_product_title

      )



# class LogEntryOnline(models.Model):
#     user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='log_entries_online')
#     action_category = models.CharField(max_length=10)  # 'CREATE', 'UPDATE', 'DELETE'
#     timestamp = models.DateTimeField(auto_now_add=True)
#     details = models.TextField(
