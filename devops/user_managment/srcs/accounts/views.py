from .models import Profile, RelationError, UnknownRelationError
from .serializers import  UserRegisterSerializer,  ProfileSerializer, UserSerializer #,ProfileUpdateSerializer,
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.decorators import api_view, renderer_classes, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from django.http import Http404
from django.http import HttpResponseForbidden
from .permissions import ProfilePermisson

# CreateAPIView : Used for create-only endpoints.

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.order_by('elo').all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, ProfilePermisson]
    
    
    @action(detail=False, url_path=r'relation/(?P<relation_type>[-\w]+)')
    def get_relation(self, request, relation_type):
        try:
            profile: Profile = Profile.get_profile(self.request.user)
            qs = profile.get_relation_profile_qs(relation_type)
        except RelationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'Error': e.message})
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, url_path=r'update_relation/(?P<relation_type>[-\w]+)/(?P<pk>[-\w]+)')
    def update_relation(self, request, relation_type, pk):
        try:
            Profile.get_profile(request.user).update_relations(int(pk), relation_type)
        except RelationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'Error': e.message})
        except ObjectDoesNotExist:
            raise Http404
        return Response(status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        return HttpResponseForbidden("you can't create a profile directly")


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer
from decouple import config

CLIENT_ID = config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")
REDIRECT_URI = config("REDIRECT_URI")


###### Simple Token JWT ######
@api_view(['POST'])
def login(request):
    #Verification du mdp et du username
    user = get_object_or_404(User, username=request.data['username'])
    if not user.check_password(request.data['password']):
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    #Generation des tokens jwt
    refresh = RefreshToken.for_user(user)
    serializer = UserSerializer(instance=user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": serializer.data
    })

#@api_view(['POST'])
#def signup(request):
#    #initialiser le nouvel user
#    serializer = UserSerializer(data=request.data)
#    if serializer.is_valid():
#        serializer.save()
#        user = User.objects.get(username=request.data['username'])
#        user.set_password(request.data['password']) #hash le mdp
#        user.save()
#        #Generation des token JWT
#        refresh = RefreshToken.for_user(user)
#        return Response({
#            "refresh": str(refresh),
#            "access": str(refresh.access_token),
#            "user": serializer.data
#        })
#    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def signup(request):
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            user = User.objects.get(username=request.data['username'])
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data
            })
        except IntegrityError:
            return Response(
                {"username": ["Un utilisateur avec ce nom existe déjà."]},
                status=status.HTTP_400_BAD_REQUEST
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_token(request):
    return Response("Passed for {}".format(request.user.email))

############

###### JWT Token + Oauth2 42 Token ######

@api_view(['GET'])
def oauth2_login(request):
    # Redirige l'utilisateur vers l'authentification 42
    oauth_url = f"https://api.intra.42.fr/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code"
    return Response(oauth_url)

@api_view(['GET'])
def oauth2_callback(request):
    import requests
    #recupere le code dauth envoye par 42
    code = request.GET.get('code')
    if not code:
        return Response({"error": "Missing code"}, status=400)
    
    #echange le code obtenu par un access token
    token_response = requests.post(
        'https://api.intra.42.fr/oauth/token',
        data={
            'grant_type': 'authorization_code',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
            'redirect_uri': REDIRECT_URI,
        }
    )
    if token_response.status_code != 200:
        return Response({"error": "Failed to fetch access token"}, status=400)
    
    token_data = token_response.json()
    access_token = token_data.get('access_token')

    # Récupère les informations utilisateur depuis l'API de 42
    user_info_response = requests.get(
        'https://api.intra.42.fr/v2/me',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if user_info_response.status_code != 200:
        return Response({"error": "Failed to fetch user info"}, status=400)

    user_info = user_info_response.json()
    username = user_info.get('login')
    email = user_info.get('email')
    profile_picture = user_info.get('image', {}).get('link')


    # Vérifie si l'utilisateur existe déjà ou crée-le
    user, created = User.objects.get_or_create(username=username, defaults={'email': email})

    # Génération du token JWT
    refresh = RefreshToken.for_user(user)

    # Passe "is_42_user=True" au contexte du serializer
    serializer = UserSerializer(user, context={'is_42_user': True, 'profile_picture': profile_picture}, data=request.data, partial=True)
    if serializer.is_valid():
        user = serializer.save()
        from accounts.models import Profile
        profile = Profile.objects.get(user=user)

        print(user.username, profile.avatar, profile)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": serializer.data,
    })

############
