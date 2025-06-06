from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from Products.models import Product


class LogEntry(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]

    action_category = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    summary = models.CharField(max_length=255, blank=True)

    # User will be set to null, but username_snapshot will preserve identity
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='log_entries')
    username_snapshot = models.CharField(max_length=150, blank=True, null=True)

    # Product reference is optional, but we don’t store product metadata
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200, blank=True, null=True)

    # Only used on UPDATEs
    changed_fields = models.JSONField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.username_snapshot and self.user:
            self.username_snapshot = self.user.username
        if self.action_category == 'CREATE' or self.action_category == 'UPDATE':
            self.product_name = self.product.title if self.product else 'Unknown Product'
        if self.action_category == 'DELETE':
            self.product_name = self.resolved_product_name()
      
        super().save(*args, **kwargs)

    def resolved_product_name(self):
        if self.product_name:
            return self.product_name
        elif isinstance(self.changed_fields, dict) and "Product Name" in self.changed_fields:
            return self.changed_fields["Product Name"]
        elif self.product and hasattr(self.product, 'title'):
            return self.product.title
        return "N/A"
    
    def resolved_part_number(self):
        if isinstance(self.changed_fields, dict) and "Part Number" in self.changed_fields:
            part_number_field = self.changed_fields["Part Number"]
            if isinstance(part_number_field, dict) and "new_value" in part_number_field: # checks if the field has another dict of values
                return part_number_field["new_value"] # if the field is a dict, return the new value
            return part_number_field # no dict, just has the part number
        elif self.product and hasattr(self.product, 'product_ID'):
            return self.product.product_ID
        return "N/A"

    def __str__(self):
        return f"[{self.timestamp}] {self.action_category} by {self.username_snapshot or 'Unknown'}"
    


# @receiver(pre_save, sender=Product)
# def log_product_action(sender, instance, **kwargs):
#     if instance.pk is not None:
#       old_instance = sender.objects.get(pk=instance.pk)
#       changes = {}
#       for field in instance._meta.fields:
#           if field.name == 'printed':
#             continue
#           elif field.name == 'modified_by':
#             continue
#           if getattr(instance, field.attname) != getattr(old_instance, field.attname):
#               changes[field.attname] = {
#                   'old_value': getattr(old_instance, field.attname),
#                   'new_value': getattr(instance, field.attname)
#               }
#       instance._changes_before_save = changes
#       instance.prev_product_title = old_instance.title

# @receiver(post_save, sender=Product)
# def log_creation_adding_or_editing(sender, instance, created, **kwargs):
#   # Your post-save logic here
#   if created:
#       details = (
#         f"Product {instance.title} was created by {instance.user}\n"
#         f"Part Number: {instance.product_ID}\n"
#         f"Location ID: {instance.location_ID}\n"
#         f"Quantity: {instance.quantity}\n"
#         f"Vendor: {instance.vendor}\n"
#         f"Description: {instance.description}"
#     )
#       LogEntry.objects.create(
#           user=instance.user,
#           action_category='CREATE',
#           details=details,
#           product_name=instance.title
#       )
#   else:
#     if hasattr(instance, '_changes_before_save') and instance._changes_before_save:
#       changes = instance._changes_before_save
#       del instance._changes_before_save
#       details = f'Product {instance.prev_product_title} was updated.\n'
#       for field, values in changes.items():
#             field_name = field_names.get(field, field)  # Use the user-friendly name if available, otherwise use the field name
#             details += f'{field_name} was changed from {values["old_value"]} to {values["new_value"]}\n'
#       LogEntry.objects.create(
#           user=instance.modified_by,
#           action_category='UPDATE',
#           details=details,
#           product_name=instance.prev_product_title

#       )



# class LogEntryOnline(models.Model):
#     user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='log_entries_online')
#     action_category = models.CharField(max_length=10)  # 'CREATE', 'UPDATE', 'DELETE'
#     timestamp = models.DateTimeField(auto_now_add=True)
#     details = models.TextField(
