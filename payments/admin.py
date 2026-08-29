from django.contrib import admin
from .models import LandlordPayout, PaymentReceipt, RentInstallment
admin.site.register(RentInstallment)
admin.site.register(PaymentReceipt)
admin.site.register(LandlordPayout)
