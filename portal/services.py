from django.contrib.auth.models import AnonymousUser

from .models import OperationAudit, PersonProfile


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


def get_person_for_user(user):
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return None
    return getattr(user, "person_profile", None)


def can_manage_people(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    person = get_person_for_user(user)
    return bool(person and person.role in {PersonProfile.Role.DEPARTMENT_ADMIN, PersonProfile.Role.MANAGER})


def can_manage_conduct(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    person = get_person_for_user(user)
    return bool(
        person
        and (
            person.can_manage_conduct
            or person.role in {PersonProfile.Role.DEPARTMENT_ADMIN, PersonProfile.Role.MANAGER}
        )
    )


def can_manage_resources(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    person = get_person_for_user(user)
    return bool(
        person
        and person.role in {
            PersonProfile.Role.DEPARTMENT_ADMIN,
            PersonProfile.Role.MANAGER,
            PersonProfile.Role.INSTRUCTOR,
        }
    )


def audit(request, action, *, target=None, summary="", metadata=None):
    target_type = target.__class__.__name__ if target is not None else ""
    target_id = str(getattr(target, "pk", "")) if target is not None else ""
    return OperationAudit.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary[:240],
        metadata=metadata or {},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
