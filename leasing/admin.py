from django.contrib import admin
from .models import Lease, RentalCase
admin.site.register(RentalCase)
admin.site.register(Lease)
