from rest_framework import permissions
from .models import User, Profile

class ProfilePermisson(permissions.BasePermission):
    def has_object_permission(self, request, view, obj : Profile):
        user = request.user
        if request.method not in permissions.SAFE_METHODS and obj.user != request.user:
             return False
        return True
    