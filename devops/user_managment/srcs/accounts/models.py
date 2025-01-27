from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from typing_extensions import Self
from enum import Enum, auto, unique, Flag
from django.db.models import QuerySet
from .errors import *


class RelationsUpdate(Enum):
    """
    Enum describing updating relations choice
    """
    ACCEPT_FRIEND = 'accept_friend' 
    UNFRIEND = 'unfriend'
    BLOCK = 'block'
    UNBLOCK = 'unblock'
    CREATE_REQUEST = 'create_request'
    DELETE_REQUEST = 'delete_request'

    @staticmethod
    def from_str(rel_type : str) -> Self:
        for rel in RelationsUpdate:
            if rel_type == rel.value:
                return rel
        raise UnknownRelationError(rel_type)
            
    def get_update_name(self):
        return self.value
        

class RelationsType(Enum): 
    """
    Enum describing relation status between 2 players
    """
    FRIEND = 'friends'
    NEUTRAL = 'neutral'
    BLOCK = 'blockeds'
    SELF_REQUEST = 'requested'
    OTHER_REQUEST = 'received_request'
    
    @staticmethod
    def from_str( rel_type : str) -> Self:
        for rel in RelationsType:
            if rel_type == rel.value:
                return rel
        raise UnknownRelationError(rel_type)
    
    @staticmethod
    def relation_between(profile, other : User):
        """
        return relation status between 2 profiles
        """
        profile : Profile = Profile.get_profile(profile)
        # other : User = Profile.get_profile(other).user
        if other in profile.friends.all():
            if not profile.user in other.profile.friends.all():
                raise RelationError("Unilateral Friendship")
            else:
                return RelationsType.FRIEND
        if other in profile.requested.all():
            if profile.user in other.profile.requested.all():
                raise RelationError("Bilateral request")
            else:
                return RelationsType.SELF_REQUEST
        if other in profile.other_requested.all(): # profile.user in other.profile.requested.all()
            return RelationsType.OTHER_REQUEST
        if other in profile.blockeds.all():
            return RelationsType.BLOCK
        return RelationsType.NEUTRAL

    def get_accessible_updates(self):
        if self == RelationsType.FRIEND:
            return [RelationsUpdate.UNFRIEND, RelationsUpdate.BLOCK]
        if self == RelationsType.NEUTRAL:
            return [RelationsUpdate.CREATE_REQUEST, RelationsUpdate.BLOCK]
        if self == RelationsType.BLOCK:
            return [RelationsUpdate.UNBLOCK]
        if self == RelationsType.OTHER_REQUEST:
            return [RelationsUpdate.ACCEPT_FRIEND, RelationsUpdate.DELETE_REQUEST, RelationsUpdate.BLOCK]
        if self == RelationsType.SELF_REQUEST:
            return [RelationsUpdate.DELETE_REQUEST, RelationsUpdate.BLOCK]
        
        
class Profile(models.Model):
    """
    Model qui représente des informations additionelles sur les user
    """
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    elo = models.IntegerField(default=0)
    # language
    avatar = models.ImageField(default='default.jpg', upload_to='profile_images')
    bio = models.TextField(default="j adore les c anar")
    friends = models.ManyToManyField(User, related_name='friends', blank=True)
    requested = models.ManyToManyField(User, related_name='requested', blank=True) # list of the users we sent a friend request to
    other_requested = models.ManyToManyField(User, related_name='other_requested', blank=True) # list of the users that sent us a friend request
    blockeds = models.ManyToManyField(User, related_name='blockeds', blank=True)
    is_42_user = models.BooleanField(default=False)

    @receiver(post_save, sender=User)
    def create_or_update_user_profile(sender, instance, created, **kwargs):
        """
        function to auto-update profil when associated user is created or modified (never directly called)
        """
        profile, created = Profile.objects.get_or_create(user=instance)  
        profile.save()
        
    def check_relations_integrity(self):
        """
        check if ther is no duplicated users in relations lists
        """
        as_lst = list(self.friends.all()) + list(self.requested.all()) + list(self.blockeds.all())
        if len(set(as_lst)) != len(as_lst):
            raise RelationError("some users are in more than one list")

    def remove_user_from_all_relations(self, user : User):
        """
        remove user from all relations list 
        do not save the model after!
        """
        self.friends.remove(user)
        self.requested.remove(user)
        self.blockeds.remove(user)
        self.other_requested.remove(user)
        
    def update_relations(self, other : int, new_rel : str):
        """
        update relations to new rel (if this make sense with current relation)
        """
        other = Profile.get_profile(other)
        RelationUpdater(self, other, new_rel).update_relation()
    
    def get_relation_to(self, other : User) -> RelationsType:
        """
        return relation between 2 users
        """
        self.check_relations_integrity()
        other = Profile.get_profile(other).user
        return RelationsType.relation_between(self, other) 
    
    def get_relation_manager(self, relation_type : RelationsType):
        """
        return relation list correspending to relation type
        """
        if relation_type == RelationsType.FRIEND:
            return self.friends
        if relation_type == RelationsType.SELF_REQUEST:
            return self.requested
        if relation_type == RelationsType.OTHER_REQUEST:
            return self.other_requested
        if relation_type == RelationsType.BLOCK:
            return self.blockeds
        raise RelationError("unable to return neutral user lists from profile")
    
    def get_relation_profile_qs(self, relation_type : str) -> QuerySet[Self]:
        """
        Return relation list as profile queryset
        """
        relation_type = RelationsType.from_str(relation_type)
        return Profile.objects.filter(user__in=self.get_relation_manager(relation_type).all())
    
    @staticmethod
    def get_profile(other ) -> Self:
        if isinstance(other, int):
            other = Profile.objects.get(pk=other)
        elif isinstance(other, User):
            other = Profile.objects.get(user=other)
        if isinstance(other, Profile):
            return other
        raise ObjectDoesNotExist
        
    def __str__(self):
        return self.user.username
        
class RelationUpdater():
    """
    class to manage relation between users
    Not a model !
    """
    
    def __init__(self, user : Profile, other_user : Profile, new_rel):
        self.new_rel = RelationsUpdate.from_str(new_rel)
        self.user = user
        self.other_user = other_user
        
    def save(self):
        """
        save users both users
        """
        self.user.save()
        self.other_user.save()
        
    def friend(self):
        """
        create friendship between 2 player 
        """
        if self.other_user.get_relation_to(self.user.user) is not RelationsType.SELF_REQUEST: 
            raise NoRequestNoFriendship()
        self.other_user.requested.remove(self.user.user)
        self.user.other_requested.remove(self.other_user.user)
        self.user.friends.add(self.other_user.user)
        self.other_user.friends.add(self.user.user)
    
    def unfriend(self):
        """
        stop friendship between 2 player 
        """
        if self.user.get_relation_to(self.other_user.user) != RelationsType.FRIEND:
            raise NotAFriendCanNotBeUnfriend()
        self.user.friends.remove(self.other_user.user)
        self.other_user.friends.remove(self.user.user)
        
    def block(self):
        """
        block other user
        """
        if self.user.get_relation_to(self.other_user.user) == RelationsType.BLOCK:
            raise BlockedTwice()
        if self.user.get_relation_to(self.other_user.user) == RelationsType.FRIEND:
            self.unfriend()
        self.user.remove_user_from_all_relations(self.other_user.user)
        self.user.blockeds.add(self.other_user.user)
            
    def unblock(self):
        """
        unblock other user
        """
        if self.other_user.user not in self.user.blockeds.all():
            raise NotBlocked()
        self.user.blockeds.remove(self.other_user.user)
        if self.user.user in self.other_user.requested.all():
            self.user.other_requested.add(self.other_user.user)
        
    def create_request(self):
        """
        create request other user
        """
        if self.user.user in self.other_user.other_requested.all(): # ou if self.other_user.user in self.user.requested
            raise AlreadyRequested()
        if self.user.user not in self.other_user.blockeds.all():
            self.other_user.other_requested.add(self.user.user)
        self.user.requested.add(self.other_user.user)
        
    def delete_request(self):
        """
        delete a friend request
        """
        if self.user.get_relation_to(self.other_user.user) == RelationsType.SELF_REQUEST:
            self.user.requested.remove(self.other_user.user)
            self.other_user.other_requested.remove(self.user.user)
        elif self.user.get_relation_to(self.other_user.user) == RelationsType.OTHER_REQUEST:
            self.user.other_requested.remove(self.other_user.user)
            self.other_user.requested.remove(self.user.user)
        else:
            raise AlreadyDeletedRequested()
        
    def update_relation(self):
        if self.new_rel == RelationsUpdate.ACCEPT_FRIEND:
            self.friend()
        elif self.new_rel == RelationsUpdate.UNFRIEND:
            self.unfriend()
        elif self.new_rel == RelationsUpdate.BLOCK:
            self.block()
        elif self.new_rel == RelationsUpdate.UNBLOCK:
            self.unblock()
        elif self.new_rel == RelationsUpdate.CREATE_REQUEST:
            self.create_request()
        elif self.new_rel == RelationsUpdate.DELETE_REQUEST:
            self.delete_request()
        self.save()
