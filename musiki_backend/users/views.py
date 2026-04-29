from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, RequestArtistSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all_with_deleted()
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class RequestArtistView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if request.user.role != 'listener':
            return Response(
                {'detail': 'Zaten sanatçı veya yönetici rolündesiniz.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = RequestArtistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request.user.role = 'artist'
        request.user.is_approved_artist = False
        request.user.bio = serializer.validated_data.get('bio', '')
        request.user.save(update_fields=['role', 'is_approved_artist', 'bio'])

        return Response(
            {'detail': 'Sanatçı başvurunuz alındı, admin onayı bekleniyor.'},
            status=status.HTTP_200_OK,
        )
