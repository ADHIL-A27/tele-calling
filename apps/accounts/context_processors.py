from apps.accounts.permissions import MANAGEMENT_ROLES


def role_flags(request):
    return {"management_roles": [r.value for r in MANAGEMENT_ROLES]}
