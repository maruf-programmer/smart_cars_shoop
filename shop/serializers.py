from rest_framework import serializers
from .models import Car, Booking, CartItem, Order, OrderItem
from datetime import date, timedelta

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    car_details = CarSerializer(source='car', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'car', 'car_details', 'client_name', 'client_phone', 'client_email', 'booking_date', 'start_time', 'end_time', 'status', 'created_at']

    def validate_booking_date(self, value):
        min_date = date.today() + timedelta(days=1)
        if value < min_date:
            raise serializers.ValidationError("Booking date must be at least 1-2 days in the future.")
        return value

    def validate(self, data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time.")
        return data

class CartItemSerializer(serializers.ModelSerializer):
    car_details = CarSerializer(source='car', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'session_id', 'car', 'car_details', 'apply_discount', 'created_at']

class OrderItemSerializer(serializers.ModelSerializer):
    car_details = CarSerializer(source='car', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'car', 'car_details', 'price', 'discount_applied', 'discount_amount']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'client_name', 'client_phone', 'client_email', 
            'payment_type', 'credit_months', 'interest_rate', 
            'total_price', 'monthly_payment', 'status', 'created_at', 'items'
        ]
