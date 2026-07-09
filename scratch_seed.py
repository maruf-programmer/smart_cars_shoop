import os
import django
from decimal import Decimal

# Configure settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'car_shop_project.settings')
django.setup()

from shop.models import Car

def seed():
    # Clear existing cars to avoid duplication
    Car.objects.all().delete()
    
    # Create Tesla
    Car.objects.create(
        brand="Tesla",
        model="Model S",
        year=2023,
        price=Decimal("89000.00"),
        color="Qizil",
        engine="Electric",
        transmission="Automatic",
        mileage=5000,
        description="Premium to'liq elektr haydovchi, avtopilot va super tezlanishga ega sedan. Bir quvvat olishda 650 km masofani bosib o'tadi.",
        image_url="/static/shop/images/tesla.jpg"
    )
    
    # Create BMW
    Car.objects.create(
        brand="BMW",
        model="M5 Competition",
        year=2022,
        price=Decimal("110000.00"),
        color="Ko'k",
        engine="4.4L V8 Twin-Turbo",
        transmission="Automatic",
        mileage=12000,
        description="M-power kuch va tezlikni o'zida birlashtirgan o'ta tezkor lyuks sport sedan.",
        image_url="/static/shop/images/bmw.jpg"
    )
    
    # Create Chevrolet Tahoe
    Car.objects.create(
        brand="Chevrolet",
        model="Tahoe RST",
        year=2023,
        price=Decimal("75000.00"),
        color="Qora",
        engine="6.2L V8 VVT",
        transmission="Automatic",
        mileage=8000,
        description="Oila uchun juda qulay, keng va hashamatli yirik o'lchamli premium SUV yo'ltanlamas.",
        image_url="/static/shop/images/tahoe.jpg"
    )
    
    print("Database successfully seeded with 3 cars!")

if __name__ == "__main__":
    seed()
