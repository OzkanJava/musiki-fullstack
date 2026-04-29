from rest_framework.permissions import BasePermission


class IsListener(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('listener', 'artist', 'admin')
        )


class IsArtist(BasePermission):
    """Onaylanmış sanatçı veya admin."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                (request.user.role == 'artist' and request.user.is_approved_artist)
                or request.user.role == 'admin'
            )
        )


class IsOwnerOrAdmin(BasePermission):
    """Object sahibi veya admin. has_object_permission seviyesinde çalışır."""
    def has_object_permission(self, request, view, obj):
        # obj.artist alanı olan modeller için (Song, Album)
        return obj.artist == request.user or request.user.role == 'admin'


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )
