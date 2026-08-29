from django.urls import path
from .my_properties_views import my_properties, property_manage
from .draft_delete import property_delete_draft

urlpatterns = [
    path('properties/', my_properties, name='my_properties'),
    path('properties/<str:property_id>/manage/', property_manage, name='property_manage'),
    path('properties/<str:property_id>/delete-draft/', property_delete_draft, name='property_delete_draft'),
]
