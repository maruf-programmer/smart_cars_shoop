from django.db import models
from django.core.exceptions import ValidationError
from datetime import date, timedelta

class Car(models.Model):
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    color = models.CharField(max_length=50)
    engine = models.CharField(max_length=100)
    transmission = models.CharField(max_length=50)
    mileage = models.IntegerField()
    description = models.TextField(blank=True, default="")
    image_url = models.TextField(blank=True, default="")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.year} {self.brand} {self.model} (${self.price})"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bookings')
    client_name = models.CharField(max_length=150)
    client_phone = models.CharField(max_length=50)
    client_email = models.EmailField()
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Must be booked at least 1 day in advance (or today + 1 day)
        min_date = date.today() + timedelta(days=1)
        if self.booking_date < min_date:
            raise ValidationError("Booking date must be at least 1-2 days in the future.")
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking by {self.client_name} for {self.car} on {self.booking_date}"

class CartItem(models.Model):
    session_id = models.CharField(max_length=255)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    apply_discount = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.session_id} - {self.car} (discount: {self.apply_discount})"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('Credit', 'Credit'),
    ]

    client_name = models.CharField(max_length=150)
    client_phone = models.CharField(max_length=50)
    client_email = models.EmailField()
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='Cash')
    credit_months = models.IntegerField(null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.client_name} (${self.total_price})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_applied = models.BooleanField(default=False)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"OrderItem {self.id} in Order {self.order_id}"
