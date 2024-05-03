
from typing import List

from django.db import models
# from base.models import User, Quiz, Category
from base.models import User, Category
from quiz.models import Quiz


import uuid

class DateTimeField(models.Model):
 updated_at = models.DateTimeField(auto_now_add=True)
 created_at = models.DateTimeField(auto_now=True)
 
 class Meta:
  abstract = True
  
class PostComments(DateTimeField):
 body = models.CharField(max_length=300)
 user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
 post = models.ForeignKey('Posts', on_delete=models.CASCADE)

#  class Meta:
#    order = '-created_at'
 
 def __str__(self):
  return self.body

class PostImages(models.Model):
 image = models.URLField()
 post = models.ForeignKey('Posts', on_delete=models.CASCADE)
 
 def __str__(self):
  return self.post.caption

#Create your models here.
class Posts(DateTimeField):
 id = models.UUIDField(default=uuid.uuid4, primary_key=True)
 posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_by')
 likes = models.ManyToManyField(User, related_name='likes')
 quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE)
 caption = models.CharField(max_length=500, null=True, blank=True)
 community = models.ForeignKey('Community', blank=True, null=True, on_delete=models.CASCADE)
 
 def __str__(self):
  return self.posted_by.username

class Community(DateTimeField):
 id = models.UUIDField(primary_key=True, default=uuid.uuid4)
 participants = models.ManyToManyField(User)
 requests = models.ManyToManyField(User, related_name='requests', blank=True)
 name = models.TextField(max_length=200)
 description = models.CharField(max_length=500, null=True, blank=True)
 display_picture = models.URLField(null=True, blank=True)
 owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owner', default=None)
 join_with_request = models.BooleanField(default=True)
 allow_categories = models.ManyToManyField(Category)
 
 @staticmethod
 def check_for_user_communities(user: User, name: str):
        # Check if a community with the given name already exists
        if Community.objects.filter(name__iexact=name).exists():
            raise ValueError("A community with this name already exists.")

        # Check if the user has too many communities
        if Community.objects.filter(owner=user).count() >= 5:
            raise ValueError("Too many communities are associated with this account. (Delete some and proceed).")

 def is_community_owner(self, user: User):
   if self.owner.id != user.id:
     raise ValueError('You are not permitted to modify actions in this community')

 def am_i_a_member(self, user:User):
   if not self.participants.filter(id=user.id).exists():
     raise ValueError('You must be a member of this community to post on their feed')

 def accept_request(self, user_id: str):

  user: User = User.objects.get(id=user_id)
  # First check if the user is in the requests
  if not self.requests.filter(id=user_id).exists():
    raise ValueError('User has not requested to join this community')

  self.participants.add(user)
  self.requests.remove(user)
  #Notify the user
  self.save()
 
 def reject_request(self, user_id: str):
  user: User = User.objects.get(id=user_id)
  #Remove from request list and notify user
  self.requests.remove(user)
  self.save()
 
 def remove_user(self, user: User):
  self.participants.remove(user)
  self.save()
 
 def remove_post(self, post: Posts):
  self.posts.remove(post)
  #notify_user_on_community()
  self.save()
 
   
 def __str__(self):
  return self.name
 


