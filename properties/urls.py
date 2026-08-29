from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('properties/create/', views.property_create, name='property_create'),
    path('properties/<str:property_id>/edit/', views.property_edit, name='property_edit'),
    path('properties/<str:property_id>/', views.property_detail, name='property_detail'),
]
