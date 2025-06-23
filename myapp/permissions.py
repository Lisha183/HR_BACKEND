from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True

        if request.user and request.user.is_authenticated:

            if hasattr(obj, 'user') and obj.user == request.user:
                return True
            if hasattr(obj, 'employee') and obj.employee == request.user:
                return True

        return False

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated