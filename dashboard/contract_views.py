from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from contracts.models import Contract


@login_required
def contract_document(request, contract_id):
    contract = get_object_or_404(
        Contract.objects.select_related('lease__tenant', 'lease__landlord'),
        contract_id=contract_id,
    )
    user = request.user
    is_staff = user.is_staff or user.is_superuser
    is_party = (
        (contract.contract_type == 'TENANT' and contract.lease.tenant_id == user.pk)
        or (contract.contract_type == 'LANDLORD' and contract.lease.landlord_id == user.pk)
    )
    if not (is_staff or is_party):
        raise Http404
    if contract.status != 'VALIDATED' or not contract.signed_document:
        raise Http404

    response = FileResponse(
        contract.signed_document.open('rb'),
        as_attachment=True,
        filename=contract.signed_document.name.rsplit('/', 1)[-1],
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response
