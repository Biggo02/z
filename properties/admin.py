from django.contrib import admin
from .models import (
    Bathroom, Bedroom, Favorite, Kitchen, LivingRoom, Property,
    PropertyDeclaration, PropertyFeature, PropertyPhoto, PropertyPublication,
    PropertyType, Toilet,
)

admin.site.register(PropertyType)
admin.site.register(Property)
admin.site.register(PropertyFeature)
admin.site.register(Bedroom)
admin.site.register(LivingRoom)
admin.site.register(Kitchen)
admin.site.register(Bathroom)
admin.site.register(Toilet)
admin.site.register(PropertyPhoto)
admin.site.register(PropertyPublication)
admin.site.register(PropertyDeclaration)
admin.site.register(Favorite)
