from functools import wraps

from django.core.exceptions import PermissionDenied

from apps.accounts.models import Role

MANAGEMENT_ROLES = {Role.ADMIN}
ADMIN_ROLES = {Role.ADMIN}


def role_required(*roles):
    """View decorator restricting access to the given Role values."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.role not in roles:
                raise PermissionDenied("You do not have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def can_manage_leads(user):
    return user.is_authenticated and user.role in ADMIN_ROLES


def can_assign_leads(user):
    return user.is_authenticated and user.role in MANAGEMENT_ROLES


def can_view_all_leads(user):
    return user.is_authenticated and user.role in MANAGEMENT_ROLES


def can_access_lead(user, lead):
    """Object-level check: telecallers may only access leads currently
    owned by them; admins can access everything."""
    if not user.is_authenticated:
        return False
    if user.role in MANAGEMENT_ROLES:
        return True
    if user.role == Role.TELECALLER:
        return lead.current_owner_id == user.id
    return False
