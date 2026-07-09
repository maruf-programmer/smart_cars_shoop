from django.shortcuts import render
from django.db import transaction
from django.db.models import Sum, Count
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Car, Booking, CartItem, Order, OrderItem
from .serializers import CarSerializer, BookingSerializer, CartItemSerializer, OrderSerializer
from decimal import Decimal

# Frontend Page Views
def index_view(request):
    return render(request, 'shop/index.html')

def admin_dashboard_view(request):
    return render(request, 'shop/admin.html')

# API Viewsets
class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.all().order_by('-created_at')
    serializer_class = CarSerializer

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-booking_date', '-start_time')
        email = self.request.query_params.get('email')
        phone = self.request.query_params.get('phone')
        ids = self.request.query_params.get('ids')
        
        if email:
            queryset = queryset.filter(client_email=email)
        if phone:
            queryset = queryset.filter(client_phone=phone)
        if ids:
            try:
                id_list = [int(x) for x in ids.split(',') if x.strip().isdigit()]
                queryset = queryset.filter(id__in=id_list)
            except ValueError:
                pass
            
        return queryset

class CartViewSet(viewsets.ViewSet):
    def list(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({"error": "session_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        items = CartItem.objects.filter(session_id=session_id)
        serializer = CartItemSerializer(items, many=True)
        
        # Calculate pricing
        subtotal = Decimal('0.00')
        discount = Decimal('0.00')
        
        for item in items:
            subtotal += item.car.price
        
        # Apply 20% discount on one car if there are at least 2 cars in the cart
        if items.count() >= 2:
            discounted_item = items.filter(apply_discount=True).first()
            # If nothing is selected, default to none (user must toggle it, as per requirements)
            if discounted_item:
                discount = discounted_item.car.price * Decimal('0.20')
        
        total_price = subtotal - discount
        
        return Response({
            "items": serializer.data,
            "subtotal": float(subtotal),
            "discount": float(discount),
            "total_price": float(total_price),
            "discount_allowed": items.count() >= 2
        })

    def create(self, request):
        session_id = request.data.get('session_id')
        car_id = request.data.get('car')
        
        if not session_id or not car_id:
            return Response({"error": "session_id and car fields are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            car = Car.objects.get(id=car_id)
        except Car.DoesNotExist:
            return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Add to cart
        cart_item = CartItem.objects.create(session_id=session_id, car=car)
        
        # If cart has >= 2 items and no item has apply_discount=True, we can default the first one or leave it False
        # The requirements state: "bu chegirmani ikkita vaomobilning bittsiga yani mijoz xo birinchisiga xo ikkinchisiga chegirmani qoyib sotib oladigan bolsin"
        # Let's let client toggle it.
        
        return Response(CartItemSerializer(cart_item).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def toggle_discount(self, request, pk=None):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        session_id = item.session_id
        items_count = CartItem.objects.filter(session_id=session_id).count()
        
        if items_count < 2:
            return Response({"error": "Discount can only be applied if there are 2 or more cars in the cart."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Turn off discount for all other items in this cart session
        CartItem.objects.filter(session_id=session_id).update(apply_discount=False)
        
        # Turn on discount for this item
        item.apply_discount = True
        item.save()
        
        return Response({"message": "Discount applied to this item successfully"})

    def destroy(self, request, pk=None):
        try:
            item = CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            return Response({"error": "Cart item not found"}, status=status.HTTP_404_NOT_FOUND)
        
        session_id = item.session_id
        item.delete()
        
        # If cart items count becomes < 2, disable all discounts
        if CartItem.objects.filter(session_id=session_id).count() < 2:
            CartItem.objects.filter(session_id=session_id).update(apply_discount=False)
            
        return Response({"message": "Item removed from cart"}, status=status.HTTP_204_NO_CONTENT)

class CheckoutViewSet(viewsets.ViewSet):
    def create(self, request):
        session_id = request.data.get('session_id')
        client_name = request.data.get('client_name')
        client_phone = request.data.get('client_phone')
        client_email = request.data.get('client_email')
        payment_type = request.data.get('payment_type', 'Cash')
        credit_months = request.data.get('credit_months')
        
        if not all([session_id, client_name, client_phone, client_email]):
            return Response({"error": "session_id, client_name, client_phone, and client_email are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_items = CartItem.objects.filter(session_id=session_id)
        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate totals
        subtotal = Decimal('0.00')
        discount = Decimal('0.00')
        discounted_item = None
        
        for item in cart_items:
            subtotal += item.car.price
            
        if cart_items.count() >= 2:
            discounted_item = cart_items.filter(apply_discount=True).first()
            if discounted_item:
                discount = discounted_item.car.price * Decimal('0.20')
        
        base_total = subtotal - discount
        
        interest_rate = None
        monthly_payment = None
        final_price = base_total
        
        if payment_type == 'Credit':
            if not credit_months:
                return Response({"error": "credit_months is required for Credit purchases"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert credit_months to int
            try:
                credit_months = int(credit_months)
            except ValueError:
                return Response({"error": "credit_months must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Interest rates:
            # 6 months: 6%
            # 10 months: 10%
            # 12 months: 12%
            # 24 months: 14%
            # 3 years (36 months): 20%
            rate_map = {
                6: Decimal('6.0'),
                10: Decimal('10.0'),
                12: Decimal('12.0'),
                24: Decimal('14.0'),
                36: Decimal('20.0')
            }
            
            if credit_months not in rate_map:
                return Response({"error": f"Invalid credit duration. Must be one of {list(rate_map.keys())}"}, status=status.HTTP_400_BAD_REQUEST)
                
            interest_rate = rate_map[credit_months]
            final_price = base_total * (Decimal('1.0') + (interest_rate / Decimal('100.0')))
            monthly_payment = final_price / Decimal(str(credit_months))
            
        with transaction.atomic():
            # Create Order
            order = Order.objects.create(
                client_name=client_name,
                client_phone=client_phone,
                client_email=client_email,
                payment_type=payment_type,
                credit_months=credit_months,
                interest_rate=interest_rate,
                total_price=final_price,
                monthly_payment=monthly_payment,
                status='Pending'
            )
            
            # Create Order Items and update Car availability
            for item in cart_items:
                is_discounted = (item == discounted_item)
                item_discount = item.car.price * Decimal('0.20') if is_discounted else Decimal('0.00')
                
                OrderItem.objects.create(
                    order=order,
                    car=item.car,
                    price=item.car.price,
                    discount_applied=is_discounted,
                    discount_amount=item_discount
                )
                
                # Mark car as unavailable (sold)
                # car = item.car
                # car.is_available = False
                # car.save()
                
            # Clear Cart
            cart_items.delete()
            
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class DashboardStatsView(views.APIView):
    def get(self, request):
        total_sales = Order.objects.aggregate(total=Sum('total_price'))['total'] or 0.0
        orders_count = Order.objects.count()
        credit_orders_count = Order.objects.filter(payment_type='Credit').count()
        cash_orders_count = Order.objects.filter(payment_type='Cash').count()
        
        bookings_count = Booking.objects.count()
        pending_bookings = Booking.objects.filter(status='Pending').count()
        approved_bookings = Booking.objects.filter(status='Approved').count()
        
        # Recent Bookings and Orders
        recent_bookings = Booking.objects.all().order_by('-created_at')[:10]
        recent_orders = Order.objects.all().order_by('-created_at')[:10]
        
        # Bookings Serializer (using standard serializer)
        bookings_data = BookingSerializer(recent_bookings, many=True).data
        orders_data = OrderSerializer(recent_orders, many=True).data
        
        return Response({
            "total_sales_revenue": float(total_sales),
            "orders_count": orders_count,
            "credit_orders_count": credit_orders_count,
            "cash_orders_count": cash_orders_count,
            "bookings_count": bookings_count,
            "pending_bookings_count": pending_bookings,
            "approved_bookings_count": approved_bookings,
            "recent_bookings": bookings_data,
            "recent_orders": orders_data
        })

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

