from rest_framework import serializers
from typing import Any

#Models Import
from .models import Community, Posts, PostImages, PostComments

# base models
from base.models import User
from serializers import CategorySerializer

class PopularCommunitiesSerializer(serializers.ModelSerializer):
    participants_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Community
        fields = ['id', 'name', 'display_picture', 'created_at', 'participants_count']
        
    def get_participants_count(self, obj: Any):
     return obj.participants.count()

class ImageSerializer(serializers.ModelSerializer):
   image = serializers.ImageField()

class PostedBySerializer(serializers.ModelSerializer):
   username = serializers.CharField()
   profile_image = serializers.URLField( required=False)
   id = serializers.UUIDField()

   class Meta:
      model = User
      fields = ['profile_image', 'username', 'id', 'account_type']

class PostSerializer(serializers.ModelSerializer):
    likes_count = serializers.SerializerMethodField()
    posted_by = PostedBySerializer(read_only=True)
    quiz_id = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        fields = ['likes_count','posted_by','quiz_id','images','caption','created_at', 'id', 'comments_count']
        model = Posts

    def get_likes_count(self, obj: Posts):
        return obj.likes.count()

    def get_quiz_id(self, obj: Posts):
        return obj.quiz.id if obj.quiz else ''
    
    def get_comments_count(self, obj:Posts):
       comments_count = PostComments.objects.filter(post__id=obj.id).count()
       return comments_count

    def get_images(self, obj: Posts):
        images = PostImages.objects.filter(post__id=obj.id).values('id', 'image')
        return list(images)

class MyCommunities(serializers.ModelSerializer):
   class Meta:
    model = Community
    fields = ['id', 'name', 'display_picture']

class PostCommentSerializer(serializers.ModelSerializer):
   user = PostedBySerializer(read_only=True)

   class Meta:
      fields = '__all__'
      model = PostComments


class CommunityDetailsSerializer(serializers.ModelSerializer):
   
   participants_count = serializers.SerializerMethodField(read_only=True)
   posts_count = serializers.SerializerMethodField(read_only=True)
   requests_count = serializers.SerializerMethodField(read_only=True)
   created_by = serializers.CharField(source='owner.username', read_only=True)
   allow_categories = CategorySerializer(many=True)
   
   class Meta:
      exclude = ['participants', 'requests', 'owner']
      model = Community

   def get_participants_count(self, obj: Community):
      return obj.participants.count()
   
   def get_posts_count(self, obj: Community):
      posts = Posts.objects.filter(community=obj).count()
      return posts
   
   def get_requests_count(self, obj:Community):
      return obj.requests.count()





