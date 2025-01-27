from django.test import Client
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .errors import *
from .models import Profile, User, RelationsType, RelationsUpdate

# class ProfileCreationTest(TestCase):
#     data = {
#         'username' : 'coucou',
#         'password' : 'le loup',
#         'repeated_password' : 'le loup'
#     }

#     def setUp(self):
#         self.client = APIClient()
        
#     def test_creation(self):
#         rsp = self.client.post(reverse('register'), data=self.data, format='json')
#         self.assertTrue(Profile.objects.filter(user__username='coucou').count() == 1)
#         self.assertTrue(rsp.status_code == status.HTTP_201_CREATED)
        
#     def test_not_matching_password(self):
#         data2 = {
#             'username' : 'coucou2',
#             'password' : 'le loup2',
#             'repeated_password' : 'le loup'
#         }
#         rsp = self.client.post(reverse('register'), data=data2, format='json')
#         self.assertContains(rsp, 'Password Does not match', status_code=status.HTTP_400_BAD_REQUEST)
        
#     def test_duplicated_username(self):
#         self.client.post(reverse('register'), data=self.data, format='json')
#         rsp = self.client.post(reverse('register'), data=self.data, format='json')
#         self.assertContains(rsp, 'A user with that username already exists',status_code=status.HTTP_400_BAD_REQUEST)
        
def update_rel(action, client, other):
        return client.get(reverse('profile-update-relation', args=[action.value,other.user.pk]))
         
def create_friendship(client, user,  other_username):
    other = User.objects.get(username=other_username)
    update_rel(RelationsUpdate.CREATE_REQUEST, client, other.profile)
    other_client = APIClient()
    other_client.force_login(user=other)
    update_rel(RelationsUpdate.ACCEPT_FRIEND, other_client, user.profile)
    assert(user in other.profile.friends.all())
    assert(other in user.profile.friends.all())
     
class RelationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='acndjks', password='absdfjnjufdw')
        self.client = APIClient()
        self.client.force_login(user=self.user)
        for i in range(5):
            User.objects.create_user(username=f'user{i}', password='password')
            
    def test_basic_block(self):
        """
        Check if we can block a user
        """
        other = User.objects.get(username='user0')
        rsp = update_rel(RelationsUpdate.BLOCK, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(other.profile.user in self.user.profile.blockeds.all())
        
    def test_block_twice(self):
        """
        Check if we can block a user twice
        """
        
        #check blocking twice
        other = User.objects.get(username='user1')
        update_rel(RelationsUpdate.BLOCK, self.client, other.profile)
        rsp = update_rel(RelationsUpdate.BLOCK, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertTrue(BlockedTwice.message in rsp.json()['Error'])
        
        #check unblocking twice
        update_rel(RelationsUpdate.UNBLOCK, self.client, other.profile)
        rsp = update_rel(RelationsUpdate.UNBLOCK, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertTrue(NotBlocked.message in rsp.json()['Error'])
        self.assertTrue(other.profile.user not in self.user.profile.blockeds.all())
        
    def test_block_by_retrieving_action(self):
        """
        Check if we can block a user by retrieving the action
        """
        other = User.objects.get(username='user2')
        
        # blocking other using action sent by the server
        rsp = self.client.get(reverse('profile-detail', args=[other.pk]))
        block_url = rsp.json()['actions'][RelationsUpdate.BLOCK.value]
        rsp = self.client.get(block_url)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(other in self.user.profile.blockeds.all())
        
        #unblocking other using action sent by the server
        rsp = self.client.get(reverse('profile-detail', args=[other.pk]))
        unblock_url = rsp.json()['actions'][RelationsUpdate.UNBLOCK.value]
        rsp = self.client.get(unblock_url)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(other not in self.user.profile.blockeds.all())
        
    def test_block_then_request_then_unblock(self):
        """
        Check if we can block a user then unblock them
        """
        other = User.objects.get(username='user3')
        update_rel(RelationsUpdate.BLOCK, self.client, other.profile)
        other_client = APIClient()
        other_client.force_login(user=other)
        #other sends a friend request to user
        update_rel(RelationsUpdate.CREATE_REQUEST, other_client, self.user.profile)
        self.assertTrue(self.user in other.profile.requested.all())
        # assert that user do not see other request
        self.assertFalse(other in self.user.profile.other_requested.all())
        update_rel(RelationsUpdate.UNBLOCK, self.client, other.profile)
        # assert that user now sees the request
        self.assertTrue(other in self.user.profile.other_requested.all())

    def test_block_remove_friendship(self):
        create_friendship(self.client, self.user, 'user4')
        update_rel(RelationsUpdate.BLOCK, self.client, User.objects.get(username='user4').profile)
        self.assertTrue(User.objects.get(username='user4') in self.user.profile.blockeds.all())
        self.assertTrue(self.user not in User.objects.get(username='user4').profile.friends.all())

    def test_request(self):
        """
        Check if we can send a friend request
        """
        other = User.objects.get(username='user4')
        rsp = update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user in other.profile.other_requested.all())
        self.assertTrue(other in self.user.profile.requested.all())
        
        #check other can not send a request to user
        rsp = self.client.get(reverse('profile-detail', args=[other.pk]))
        self.assertTrue(RelationsUpdate.CREATE_REQUEST.value not in rsp.json()['actions'])
        rsp = update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertTrue(AlreadyRequested.message in rsp.json()['Error'])

    def test_accept_request(self):
        """
        Check if we can accept a friend request
        """
        create_friendship(self.client, self.user, 'user4')
        self.assertTrue(self.user in User.objects.get(username='user4').profile.friends.all())
        self.assertTrue(User.objects.get(username='user4') in self.user.profile.friends.all())
        rsp = self.client.get(reverse('profile-detail', args=[User.objects.get(username='user4').pk]))
        self.assertFalse(RelationsUpdate.ACCEPT_FRIEND.value in rsp.json()['actions'])
        self.assertFalse(RelationsUpdate.CREATE_REQUEST.value in rsp.json()['actions'])
        self.assertTrue(RelationsUpdate.UNFRIEND.value in rsp.json()['actions'])

    def test_accept_request_then_unfriend(self):
        """
        Check if we can accept a friend request then unfriend
        """
        create_friendship(self.client, self.user, 'user4')
        rsp = update_rel(RelationsUpdate.UNFRIEND, self.client, User.objects.get(username='user4').profile)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user not in User.objects.get(username='user4').profile.friends.all())
        self.assertTrue(User.objects.get(username='user4') not in self.user.profile.friends.all())
        
    def test_unfriend_by_retrieving_action(self):
        """
        Check if we can unfriend by retrieving the action
        """
        create_friendship(self.client, self.user, 'user4')
        rsp = self.client.get(reverse('profile-detail', args=[User.objects.get(username='user4').pk]))
        unfriend_url = rsp.json()['actions'][RelationsUpdate.UNFRIEND.value]
        rsp = self.client.get(unfriend_url)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user not in User.objects.get(username='user4').profile.friends.all())
        self.assertTrue(User.objects.get(username='user4') not in self.user.profile.friends.all())
        
    def test_delete_request(self):
        """
        Check if we can delete a friend request
        """
        other = User.objects.get(username='user4')
        update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        rsp = update_rel(RelationsUpdate.DELETE_REQUEST, self.client, other.profile)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user not in other.profile.other_requested.all())
        self.assertTrue(other not in self.user.profile.requested.all())
        
    def test_friendship_then_remove_request(self):
        create_friendship(self.client, self.user, 'user4')
        rsp = update_rel(RelationsUpdate.DELETE_REQUEST, self.client, User.objects.get(username='user4').profile)
        self.assertContains(rsp, AlreadyDeletedRequested.message, status_code=status.HTTP_400_BAD_REQUEST)
        
    def test_no_request_no_friendship(self):
        other = User.objects.get(username='user4')
        rsp = update_rel(RelationsUpdate.ACCEPT_FRIEND, self.client, other.profile)
        self.assertContains(rsp, NoRequestNoFriendship.message, status_code=status.HTTP_400_BAD_REQUEST)
        
    def test_friendship_by_retrieving_action(self):
        other = User.objects.get(username='user4')
        update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        other_client = APIClient()
        other_client.force_login(user=other)
        rsp = other_client.get(reverse('profile-detail', args=[self.user.pk]))
        accept_url = rsp.json()['actions'][RelationsUpdate.ACCEPT_FRIEND.value]
        rsp = other_client.get(accept_url)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user in other.profile.friends.all())
        self.assertTrue(other in self.user.profile.friends.all())

    def test_unfriend(self):
        create_friendship(self.client, self.user, 'user4')
        rsp = update_rel(RelationsUpdate.UNFRIEND, self.client, User.objects.get(username='user4').profile)
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(self.user not in User.objects.get(username='user4').profile.friends.all())
        self.assertTrue(User.objects.get(username='user4') not in self.user.profile.friends.all())
        
    def test_list_friends(self):
        for i in range(5):
            create_friendship(self.client, self.user, f'user{i}')
        rsp = self.client.get(reverse('profile-get-relation', args=[RelationsType.FRIEND.value]), format='json')
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(len(rsp.json()) == 5)
        
    def test_list_other_request(self):
        for i in range(5):
            other = User.objects.get(username=f'user{i}')
            update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        rsp = self.client.get(reverse('profile-get-relation', args=[RelationsType.SELF_REQUEST.value]), format='json')
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(len(rsp.json()) == 5)
        
    def test_list_other_request(self):
        for i in range(5):
            other = User.objects.get(username=f'user{i}')
            other_client = APIClient()
            other_client.force_login(user=other)
            update_rel(RelationsUpdate.CREATE_REQUEST, other_client, self.user.profile)
        rsp = self.client.get(reverse('profile-get-relation', args=[RelationsType.OTHER_REQUEST.value]), format='json')
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(len(rsp.json()) == 5)
        
    def test_list_block(self):
        for i in range(5):
            other = User.objects.get(username=f'user{i}')
            update_rel(RelationsUpdate.BLOCK, self.client, other.profile)
        rsp = self.client.get(reverse('profile-get-relation', args=[RelationsType.BLOCK.value]), format='json')
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(len(rsp.json()) == 5)
    
    def test_not_a_friend_can_not_unfriend(self):
        other = User.objects.get(username='user4')
        update_rel(RelationsUpdate.CREATE_REQUEST, self.client, other.profile)
        rsp = update_rel(RelationsUpdate.UNFRIEND, self.client, other.profile)
        self.assertContains(rsp, NotAFriendCanNotBeUnfriend.message, status_code=status.HTTP_400_BAD_REQUEST)
        
    def test_unknown_relation(self):
        rsp = self.client.get(reverse('profile-get-relation', args=['unknown']), format='json')
        self.assertTrue(rsp.status_code == status.HTTP_400_BAD_REQUEST)
        self.assertTrue(UnknownRelationError.message.format(relation_str='unknown') in rsp.json()['Error'])


class ProfileUpdateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='acndjks', password='absdfjnjufdw')
        self.client = APIClient()
        self.client.force_login(user=self.user)
        
    def test_update(self):
        data = {
            'bio' : 'coucou',
        }
        rsp = self.client.patch(reverse('profile-detail', args=[self.user.pk]), data=data, format='json')
        self.assertTrue(rsp.status_code == status.HTTP_200_OK)
        self.assertTrue(Profile.objects.get(user=self.user).bio == 'coucou')