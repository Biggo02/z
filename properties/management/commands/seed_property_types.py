from django.core.management.base import BaseCommand
from properties.models import PropertyType

TYPES=['Maison','Appartement','Studio','Chambre','Duplex','Villa','Autre']
class Command(BaseCommand):
    help='Create the default Fasthome property types'
    def handle(self,*args,**options):
        for order,name in enumerate(TYPES,1): PropertyType.objects.get_or_create(name=name,defaults={'order':order,'active':True})
        self.stdout.write(self.style.SUCCESS('Types de logements initialisés.'))
