from django.urls import path
from . import views
from .autosave import property_autosave
from .home_views import home_reference

urlpatterns = [
    path('', home_reference, name='home'),
    path('properties/create/', views.property_create, name='property_create'),
    path('properties/autosave/', property_autosave, name='property_autosave'),
    path('properties/<str:property_id>/edit/', views.property_edit, name='property_edit'),
    path('properties/<str:property_id>/', views.property_detail, name='property_detail'),
]
