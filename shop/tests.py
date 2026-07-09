from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Car, Booking, CartItem, Order, OrderItem
from datetime import date, time, timedelta
from decimal import Decimal

class CarModelTest(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            brand="Tesla",
            model="Model 3",
            year=2023,
            price=Decimal("45000.00"),
            color="Red",
            engine="Electric",
            transmission="Automatic",
            mileage=5000
        )

    def test_car_creation(self):
        self.assertEqual(self.car.brand, "Tesla")
        self.assertEqual(self.car.price, Decimal("45000.00"))
        self.assertEqual(str(self.car), "2023 Tesla Model 3 ($45000.00)")

class BookingValidationTest(TestCase):
    def setUp(self):
        self.car = Car.objects.create(
            brand="BMW", model="M3", year=2022, price=Decimal("70000.00"),
            color="Blue", engine="3.0L Inline 6", transmission="Manual", mileage=10000
        )

    def test_booking_past_date_fails(self):
        # Booking today or yesterday should fail because booking must be in advance (at least 1-2 days)
        booking = Booking(
            car=self.car,
            client_name="John Doe",
            client_phone="+998901234567",
            client_email="john@example.com",
            booking_date=date.today(),  # Today (not in future/advance)
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        with self.assertRaises(ValidationError):
            booking.save()

    def test_booking_invalid_time_fails(self):
        # Start time after end time
        booking = Booking(
            car=self.car,
            client_name="John Doe",
            client_phone="+998901234567",
            client_email="john@example.com",
            booking_date=date.today() + timedelta(days=2),  # Valid date
            start_time=time(14, 0),
            end_time=time(13, 0)  # Invalid (end before start)
        )
        with self.assertRaises(ValidationError):
            booking.save()

    def test_booking_valid_succeeds(self):
        booking = Booking(
            car=self.car,
            client_name="John Doe",
            client_phone="+998901234567",
            client_email="john@example.com",
            booking_date=date.today() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        try:
            booking.save()
        except ValidationError:
            self.fail("ValidationError raised unexpectedly on valid booking!")

class CartAPITest(APITestCase):
    def setUp(self):
        self.car1 = Car.objects.create(
            brand="Chevrolet", model="Malibu", year=2021, price=Decimal("25000.00"),
            color="White", engine="1.5L Turbo", transmission="Automatic", mileage=30000
        )
        self.car2 = Car.objects.create(
            brand="Chevrolet", model="Tracker", year=2022, price=Decimal("20000.00"),
            color="Black", engine="1.2L Turbo", transmission="Automatic", mileage=15000
        )
        self.session_id = "test-session-uuid"

    def test_cart_operations(self):
        # 1. Add car 1 to cart
        url = reverse('cart-list')
        response = self.client.post(url, {"session_id": self.session_id, "car": self.car1.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Get cart (1 item)
        response = self.client.get(url, {"session_id": self.session_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['subtotal'], 25000.00)
        self.assertEqual(response.data['discount'], 0.00)
        self.assertEqual(response.data['total_price'], 25000.00)
        
        # 3. Add car 2 to cart
        self.client.post(url, {"session_id": self.session_id, "car": self.car2.id}, format='json')
        response = self.client.get(url, {"session_id": self.session_id})
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(response.data['subtotal'], 45000.00)
        self.assertEqual(response.data['discount'], 0.00) # discount not selected yet
        self.assertEqual(response.data['total_price'], 45000.00)

        # 4. Toggle discount on car 1 (item 1)
        cart_items = CartItem.objects.filter(session_id=self.session_id)
        item1 = cart_items.get(car=self.car1)
        
        toggle_url = reverse('cart-toggle-discount', args=[item1.id])
        response = self.client.post(toggle_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get cart again (discount applied)
        response = self.client.get(url, {"session_id": self.session_id})
        # Discount of 20% on Malibu ($25000) = $5000
        self.assertEqual(response.data['discount'], 5000.00)
        self.assertEqual(response.data['total_price'], 40000.00)

class CheckoutAPITest(APITestCase):
    def setUp(self):
        self.car1 = Car.objects.create(
            brand="Hyundai", model="Elantra", year=2022, price=Decimal("20000.00"),
            color="Grey", engine="2.0L", transmission="Automatic", mileage=12000
        )
        self.car2 = Car.objects.create(
            brand="Kia", model="K5", year=2023, price=Decimal("30000.00"),
            color="Black", engine="2.5L", transmission="Automatic", mileage=8000
        )
        self.session_id = "checkout-session-uuid"
        
        # Add to cart
        self.cart_item1 = CartItem.objects.create(session_id=self.session_id, car=self.car1)
        self.cart_item2 = CartItem.objects.create(session_id=self.session_id, car=self.car2)
        
        # Apply discount to car 2 (K5, $30000) -> 20% of 30k000 = 6k000 discount
        self.cart_item2.apply_discount = True
        self.cart_item2.save()

    def test_checkout_cash(self):
        url = reverse('checkout-list')
        payload = {
            "session_id": self.session_id,
            "client_name": "Alisher Navoiy",
            "client_phone": "+998901112233",
            "client_email": "alisher@navoiy.uz",
            "payment_type": "Cash"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Base price = 20k000 + (30k000 * 0.8) = 20k000 + 24k000 = 44k000
        self.assertEqual(float(response.data['total_price']), 44000.00)
        self.assertEqual(response.data['payment_type'], "Cash")
        self.assertIsNone(response.data['credit_months'])
        
        # Check cart is cleared
        self.assertFalse(CartItem.objects.filter(session_id=self.session_id).exists())
        # Check Order items
        order = Order.objects.get(id=response.data['id'])
        self.assertEqual(order.items.count(), 2)

    def test_checkout_credit_12_months(self):
        url = reverse('checkout-list')
        payload = {
            "session_id": self.session_id,
            "client_name": "Bobur Mirzo",
            "client_phone": "+998904445566",
            "client_email": "bobur@mirzo.uz",
            "payment_type": "Credit",
            "credit_months": 12  # 12% markup
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Base price = 44000.00
        # Interest rate = 12%
        # Total price = 44000 * 1.12 = 49280.00
        # Monthly payment = 49280 / 12 = 4106.666...
        self.assertEqual(float(response.data['total_price']), 49280.00)
        self.assertEqual(float(response.data['interest_rate']), 12.00)
        self.assertAlmostEqual(float(response.data['monthly_payment']), 4106.67, places=2)
        
        # Check cart is cleared
        self.assertFalse(CartItem.objects.filter(session_id=self.session_id).exists())
