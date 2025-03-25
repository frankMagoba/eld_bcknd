from django.db import models

# Create your models here.

class Trip(models.Model):
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.IntegerField(default=0)
    shipping_number = models.CharField(max_length=50, blank=True, null=True, help_text="Pro or Shipping Number for driver logs")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Trip from {self.pickup_location} to {self.dropoff_location}"
