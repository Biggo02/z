from django.contrib import admin
from .models import VisitRequest

@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ('visit_id','property','requested_date','status','fasthome_approved','landlord_approved')
    list_filter = ('status','fasthome_approved','landlord_approved')
    search_fields = ('visit_id','property__property_id')
