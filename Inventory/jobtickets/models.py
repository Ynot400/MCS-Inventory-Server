from django.db import models
from django.contrib.auth.models import User
from Products.models import Product  # Adjust to your app's actual product model path


class JobTicket(models.Model):
    STATUS_CHOICES = [
        ('InProgress', 'In Progress'),
        ('Complete', 'Complete'),
    ]

    GENRE_CHOICES = [
        ('Electrical', 'Electrical'),
        ('Mechanical', 'Mechanical'),
        ('Fabrication', 'Fabrication'),
        ('Fiberglass', 'Fiberglass'),
        ('Trolling Motor Repair', 'Trolling Motor Repair'),
        ('Custom', 'Custom'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='InProgress')
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES)
    custom_genre = models.CharField(max_length=100, blank=True, null=True)

    customer_name = models.CharField(max_length=200)
    boat_name = models.CharField(max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.customer_name})"

    @property
    def effective_genre(self):
        return self.custom_genre if self.genre == "Custom" else self.genre

class JobTicketItem(models.Model):
    
    job_ticket = models.ForeignKey('JobTicket', on_delete=models.CASCADE, related_name='items')

    # Inventory product (optional)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    # One-time custom part fields (optional)
    custom_part_name = models.CharField(max_length=200, blank=True, null=True)
    custom_part_description = models.TextField(blank=True, null=True)
    custom_part_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    quantity_used = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        if self.product:
            return f"{self.quantity_used} x {self.product.title}"
        return f"{self.quantity_used} x {self.custom_part_name} (custom)"

    def is_custom_part(self):
        return self.product is None and self.custom_part_name is not None
