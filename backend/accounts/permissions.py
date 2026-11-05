from rest_framework.permissions import BasePermission


class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'role', '') == 'landlord')
