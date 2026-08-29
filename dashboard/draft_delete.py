from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from properties.models import Property

@login_required
def property_delete_draft(request, property_id):
    prop = get_object_or_404(Property.objects.select_related('publication'), property_id=property_id, owner=request.user)
    publication = getattr(prop, 'publication', None)
    if request.method != 'POST':
        return redirect('my_properties')
    if publication is None or publication.status != 'DRAFT' or prop.status != 'DRAFT':
        messages.error(request, "Ce logement ne peut plus être supprimé : sa publication n'est plus un brouillon.")
        return redirect('my_properties')
    prop.delete()
    messages.success(request, "Le brouillon du logement a été supprimé.")
    return redirect('my_properties')
