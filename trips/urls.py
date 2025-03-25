from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, HOSCalculationView, generate_log

router = DefaultRouter()
router.register(r'trips', TripViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('calculate_hos/', HOSCalculationView.as_view(), name='calculate-hos'),
    path('generate_log/', generate_log, name='generate-log'),
] 