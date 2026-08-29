from django.urls import path
from . import views

urlpatterns = [
    path('request/<str:property_id>/', views.request_visit, name='request_visit'),
    path('<str:visit_id>/fasthome-decision/', views.fasthome_visit_decision, name='fasthome_visit_decision'),
    path('<str:visit_id>/landlord-decision/', views.landlord_visit_decision, name='landlord_visit_decision'),
    path('<str:visit_id>/complete/', views.mark_visit_completed, name='mark_visit_completed'),
    path('<str:visit_id>/decision/', views.tenant_decision, name='tenant_decision'),
]
