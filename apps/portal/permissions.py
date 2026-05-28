from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.accounts.models import Account, User


PORTAL_ROLES = {
    User.CustomerRole.OWNER,
    User.CustomerRole.OPERATOR,
    User.CustomerRole.VIEWER,
}


def has_portal_access(user):
    return (
        user.is_authenticated
        and user.account_id is not None
        and user.account.status == Account.Status.ACTIVE
        and user.role in PORTAL_ROLES
    )


def portal_required(view_func):
    @wraps(view_func)
    @login_required(login_url="portal:login")
    def wrapped(request, *args, **kwargs):
        if not has_portal_access(request.user):
            return redirect("portal:access_denied")
        return view_func(request, *args, **kwargs)

    return wrapped


def owner_required(view_func):
    @wraps(view_func)
    @portal_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.CustomerRole.OWNER:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped


def application_action_allowed(user):
    return user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


def finding_acknowledge_allowed(user):
    return user.role in {User.CustomerRole.OWNER, User.CustomerRole.OPERATOR}


def finding_ignore_allowed(user):
    return user.role == User.CustomerRole.OWNER
