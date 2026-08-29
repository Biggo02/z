from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_target(request, target, fallback='home'):
    """Return a safe local redirect target or the named fallback URL."""
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return fallback
