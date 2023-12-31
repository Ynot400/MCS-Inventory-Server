from django.db import models
from django.contrib.auth.models import User
from Inventory.log_util import LoggingRetrieval








# Create your models here.
class Product(models.Model):
  title = models.TextField(max_length=200)
  location_ID = models.TextField(max_length=20)
  product_ID = models.TextField()
  quantity = models.IntegerField()
  vendor = models.TextField(max_length=200, default=None)
  date_created = models.DateTimeField(auto_now_add=True)
  user = models.ForeignKey(User, on_delete=models.DO_NOTHING, default=None)

  admin_field_price1 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=True)
  admin_field_price2 = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, editable=True)

  @property
  def admin_field_1(self):
      if self.user.is_superuser:
          return self._admin_field_price1
      return None

  @property
  def admin_field_2(self):
      # Check if the user is a superuser or admin
      if self.user.is_superuser:
          return self._admin_field_price2
      return None
  def __str__(self):
    return self.title
