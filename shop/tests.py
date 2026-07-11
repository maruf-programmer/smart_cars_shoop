from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.core.exceptions import ValidationError
from .models import Car, Booking, CartItem, Order
from datetime import date, time, timedelta
from decimal import Decimal

class CarModelTest(TestCase):
    def test_car_creation(self):
        car = Car.objects.create(
            brand="Tesla",
            model="Model 3",
            year=2023,
            price=Decimal("45000.00"),
            color="Red",
            engine="Electric",
            transmission="Automatic",
            mileage=5000
        )
        self.assertEqual(car.brand, "Tesla")
        self.assertEqual(car.price, Decimal("45000.00"))

class BookingValidationTest(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            brand="BMW", model="M3", year=2022, price=Decimal("70000.00"),
            color="Blue", engine="Electric", transmission="Manual", mileage=10000
        )

    def test_booking_past_date(self):
        booking = Booking(
            car=self.car,
            client_name="John",
            client_phone="12345",
            client_email="john@test.com",
            booking_date=date.today(),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        with self.assertRaises(ValidationError):
            booking.save()

    def test_booking_invalid_time(self):
        booking = Booking(
            car=self.car,
            client_name="John",
            client_phone="12345",
            client_email="john@test.com",
            booking_date=date.today() + timedelta(days=2),
            start_time=time(14, 0),
            end_time=time(13, 0)
        )
        with self.assertRaises(ValidationError):
            booking.save()

class CartAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.car1 = Car.objects.create(
            brand="Chevrolet", model="Malibu", year=2021, price=Decimal("25000.00"),
            color="White", engine="Gas", transmission="Automatic", mileage=30000
        )
        self.car2 = Car.objects.create(
            brand="Chevrolet", model="Tracker", year=2022, price=Decimal("20000.00"),
            color="Black", engine="Gas", transmission="Automatic", mileage=15000
        )
        self.session_id = "test-session"

    def test_cart_discount(self):
        url = reverse('cart-list')
        self.client.post(url, {"session_id": self.session_id, "car": self.car1.id}, format='json')
        self.client.post(url, {"session_id": self.session_id, "car": self.car2.id}, format='json')
        
        response = self.client.get(url, {"session_id": self.session_id})
        self.assertEqual(response.data['total_price'], 45000.00)
        
        item = CartItem.objects.get(session_id=self.session_id, car=self.car1)
        toggle_url = reverse('cart-toggle-discount', args=[item.id])
        self.client.post(toggle_url)
        
        response = self.client.get(url, {"session_id": self.session_id})
        self.assertEqual(response.data['discount'], 5000.00)
        self.assertEqual(response.data['total_price'], 40000.00)

class CheckoutAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.car1 = Car.objects.create(
            brand="Hyundai", model="Elantra", year=2022, price=Decimal("20000.00"),
            color="Grey", engine="Gas", transmission="Automatic", mileage=12000
        )
        self.car2 = Car.objects.create(
            brand="Kia", model="K5", year=2023, price=Decimal("30000.00"),
            color="Black", engine="Gas", transmission="Automatic", mileage=8000
        )
        self.session_id = "checkout-session"
        self.cart_item1 = CartItem.objects.create(session_id=self.session_id, car=self.car1)
        self.cart_item2 = CartItem.objects.create(session_id=self.session_id, car=self.car2)
        self.cart_item2.apply_discount = True
        self.cart_item2.save()

    def test_checkout_cash(self):
        url = reverse('checkout-list')
        payload = {
            "session_id": self.session_id,
            "client_name": "Alisher",
            "client_phone": "12345",
            "client_email": "alisher@test.uz",
            "payment_type": "Cash"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_price']), 44000.00)
        self.assertFalse(CartItem.objects.filter(session_id=self.session_id).exists())

    def test_checkout_credit_12_months(self):
        url = reverse('checkout-list')
        payload = {
            "session_id": self.session_id,
            "client_name": "Bobur",
            "client_phone": "12345",
            "client_email": "bobur@test.uz",
            "payment_type": "Credit",
            "credit_months": 12
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_price']), 49280.00)
        self.assertEqual(float(response.data['interest_rate']), 12.00)

    def test_checkout_credit_36_months(self):
        url = reverse('checkout-list')
        payload = {
            "session_id": self.session_id,
            "client_name": "Bobur",
            "client_phone": "12345",
            "client_email": "bobur@test.uz",
            "payment_type": "Credit",
            "credit_months": 36
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_price']), 52800.00)
        self.assertEqual(float(response.data['interest_rate']), 20.00)
