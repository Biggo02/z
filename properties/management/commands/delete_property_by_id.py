from django.core.management.base import BaseCommand, CommandError
from properties.models import Property


class Command(BaseCommand):
    help = "Supprime un bien de test/temporaire par son identifiant Fasthome."

    def add_arguments(self, parser):
        parser.add_argument("property_id")
        parser.add_argument("--yes", action="store_true")

    def handle(self, *args, **options):
        property_id = options["property_id"].strip()
        try:
            prop = Property.objects.get(property_id=property_id)
        except Property.DoesNotExist as exc:
            raise CommandError(f"Bien introuvable: {property_id}") from exc

        if not options["yes"]:
            raise CommandError(
                f"Suppression protégée. Relancez avec --yes pour supprimer {prop.property_id}."
            )

        prop.delete()
        self.stdout.write(self.style.SUCCESS(f"Bien supprimé: {property_id}"))
