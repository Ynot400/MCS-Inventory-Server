from django.db import models

# Create your models here.
class Search(models.Model):
  inventory_field = models.CharField(max_length=15)
  search_field = models.CharField(max_length=200, blank=True, null=True)