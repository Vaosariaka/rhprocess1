from rest_framework import permissions


def is_hr_or_manager(user):
    """Return True when the user has HR/Manager privileges.

    We treat staff users and users in groups named 'HR' or 'Manager' as having
    elevated privileges. This helper is used by the permission classes below
    and by some legacy Django views.
    """
    try:
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_staff', False):
            return True
        return user.groups.filter(name__in=['HR', 'Manager']).exists()
    except Exception:
        # defensive fallback
        return bool(getattr(user, 'is_staff', False))


class IsHROrReadOnly(permissions.BasePermission):
    """Allow safe methods to any user; require HR/Manager for unsafe methods.

    This is useful for planner endpoints where listing/reading is allowed to
    authenticated users but creation/modification should be restricted.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_hr_or_manager(request.user)


class IsHRManager(permissions.BasePermission):
    """Require HR/Manager privileges for all access (use on approve endpoints)."""
    def has_permission(self, request, view):
        return is_hr_or_manager(request.user)
