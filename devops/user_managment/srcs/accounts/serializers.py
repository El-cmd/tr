from rest_framework import serializers
from .models import Profile, RelationsType, RelationsUpdate
from rest_framework.fields import CurrentUserDefault
from django.contrib.auth.models import User
from django.urls import reverse

class UserRegisterSerializer(serializers.ModelSerializer):
    repeated_password = serializers.CharField(style={'input_type': 'password'}, write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'repeated_password']
        extra_kwargs = {
            'password': {'style' : {'input_type': 'password'}, 'write_only': True}
        }
    
    def save(self, **kwargs) -> User:
        #check if passwords match
        if self.validated_data['password'] != self.validated_data['repeated_password']:
            raise serializers.ValidationError({"Error": "Password Does not match"})
        return User(username=self.validated_data['username'], password=self.validated_data['password']).save()

class RelationActionMaker():
    """
    Tool class to get accesible action between request user and some other user
    get_actions returns a dict : {'action_name' : 'action_url'}
    """
    relation_update_url = 'profile-update-relation'
    
    def __init__(self, request : str, other : Profile):
        self.profile : Profile = Profile.get_profile(request.user)
        self.other = other
        self.actions = dict()
        self.create_actions()
        
    def get_action_url(self, relation_type : RelationsUpdate):
        kwargs = {
            'relation_type' : relation_type.value,
            'pk' : self.other.user.pk
        }
        
        return reverse(self.relation_update_url, kwargs=kwargs)
    
    def create_actions(self) -> dict :
        if self.profile.user == self.other.user:
            return
        for updates in self.profile.get_relation_to(self.other.user).get_accessible_updates() :
            self.actions[updates.get_update_name()] = self.get_action_url(updates)
       
class UserUpdateCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']

class ProfileSerializer(serializers.HyperlinkedModelSerializer):
    username = serializers.SerializerMethodField()
    relation = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['url', 'username', 'avatar', 'bio', 'elo', 'relation', 'actions', ]
        extra_kwargs = {
            'elo': {'read_only': True}
        }
    
    def get_relation(self, obj):
        return Profile.get_profile(self.context['request'].user).get_relation_to(obj.user).name
    
    def get_actions(self, obj):
        return RelationActionMaker(self.context['request'], obj).actions

    def get_username(self, obj):
        return obj.user.username
    
    

class UserSerializer(serializers.ModelSerializer):
    is_42_user = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    class Meta(object):
        model = User
        fields = ['id', 'username', 'password', 'email', 'is_42_user', 'profile_picture']
        extra_kwargs = {
            'password': {'write_only': True}, #Ne jamais retourner le mdp
        }
    def get_is_42_user(self, obj):
        # Vérifie si un utilisateur est connecté avec 42 (ajout via contexte ou vue)
        return self.context.get('is_42_user', False)
    
    def get_profile_picture(self, obj):
        # Retourne l'URL de la photo de profil depuis le contexte
        return self.context.get('profile_picture', None)

    def update_profile(self, instance, validated_data):
        from accounts.models import Profile
        profile = Profile.objects.get(user=instance)
        profile.avatar  = self.context.get('profile_picture', None)
        profile.is_42_user = self.context.get('is_42_user', False)
        profile.save()

        pass

    def create(self, validated_data):
        # Crée un utilisateur avec un mot de passe hashé
        super().create(validated_data)
        user = User.objects.create_user(**validated_data)
        self.update_profile(user, validated_data)
        return user
    
    def update(self, instance, validated_data):
        instance  = super().update(instance, validated_data)
        self.update_profile(instance, validated_data)
        return instance