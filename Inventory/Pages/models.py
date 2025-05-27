from django.db import models
from django.utils import timezone

# Create your models here.
class Search(models.Model):
  inventory_field = models.CharField(max_length=15)
  search_field = models.CharField(max_length=200, blank=True, null=True)


class SubmissionToken(models.Model):
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token

    @classmethod
    def is_valid(cls, token):
        return cls.objects.filter(token=token).exists()

    @classmethod
    def use(cls, token):
        deleted, _ = cls.objects.filter(token=token).delete()
        return deleted == 1
