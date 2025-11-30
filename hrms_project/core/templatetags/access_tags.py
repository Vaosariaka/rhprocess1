from django import template

from core.permissions import is_rh_user as _is_rh_user_helper

register = template.Library()


@register.filter(name='has_group')
def has_group(user, group_name):
    """Return True when the user belongs to the given Django group."""
    if not getattr(user, 'is_authenticated', False):
        return False
    try:
        return user.groups.filter(name=group_name).exists()
    except Exception:
        return False


@register.filter(name='is_rh_user')
def is_rh_user_filter(user):
    """Convenience filter using the shared is_rh_user helper."""
    return _is_rh_user_helper(user)
