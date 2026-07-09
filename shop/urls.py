from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    index_view,
    admin_dashboard_view,
    CarViewSet,
    BookingViewSet,
    CartViewSet,
    CheckoutViewSet,
    DashboardStatsView,
    OrderViewSet
)

router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='car')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'checkout', CheckoutViewSet, basename='checkout')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    # Frontend Pages
    path('', index_view, name='index'),
    path('admin-dashboard/', admin_dashboard_view, name='admin_dashboard'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard_stats'),
]
