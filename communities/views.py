
#Rest Framework Import
from rest_framework.response import Response
from rest_framework.decorators import api_view, APIView, permission_classes
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

#Django Imports
from django.db import models
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
# from django.utils import timezone

#Base Imports
from .models import Community, User, Posts, Quiz, PostImages, PostComments

#Serializers Import
from .serializers import PopularCommunitiesSerializer, CommunityDetailsSerializer, PostSerializer, MyCommunities, PostCommentSerializer

from helpers import image_uploader, post_owner, remove_image_path


@api_view(['GET'])
def get_communities(request, size: str):
 try:
  data = request.query_params
  #popular = data.get('popular', False)
  
  size = int(size)
  
  user: User = request.user
  print(user)

  communities = Community.objects.annotate(most_participants=models.Count('participants'), most_post=models.Count('posts'))
   
  if user.is_authenticated: #Exclude the community the current user is is in
    communities = communities.exclude(participants=user)
    
  communities = communities.order_by('-most_participants','-most_post')[:size]

  data = PopularCommunitiesSerializer(communities, many=True)
   
  return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)
   #here we are only going to return the [name, participants_count, display_image, if]
 except Exception as e:
  return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def join_or_leave_community(request):
 from base.helpers import notification_helper
 from base.models import Notifications
 try:
  
  user:User = request.user
  community_id = request.query_params.get('community_id')
  
  try:
   community = Community.objects.get(id=community_id)
  except Community.DoesNotExist:
   return Response({'data':{},'message':'Community with this ID does not exist'},status=status.HTTP_404_NOT_FOUND)
  
  is_already_a_member = community.participants.filter(id=user.id).exists()
  in_queue_for_approval = community.requests.filter(id=user.id).exists()
  
  if in_queue_for_approval:
   #Cancel Request
   community.requests.remove(user)
   community.save()
   return Response({'data':{},'message':'Your request has been canceled'},status=status.HTTP_200_OK)
  
  if is_already_a_member:
   #If user is already a member then remove the user
   community.participants.remove(user)
   community.save()
   return Response({'data':{},'message': f'You just left {community.name}'},status=status.HTTP_200_OK)
  
  if community.join_with_request:
   community.requests.add(user)
   community.save()
   notification_helper(community.owner,'',Notifications.NotificationType.COMMUNITY_REQUEST, '', user)
   return Response({'data':{},'message':'Request has been sent to this community admin for processing.'},status=status.HTTP_200_OK)
 
  community.participants.add(user)
  community.save()
  
  return Response({'data':{},'message':f'You joined {community.name}'},status=status.HTTP_200_OK)
  
 except Exception as e:
  return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
#@permission_classes([IsAuthenticated])
@api_view(['GET'])
def am_i_a_community_member(request):
 try:
  user:User = request.user
  
  if user.is_authenticated:
   community_id = request.query_params['community_id']
  
   community = get_object_or_404(Community, id=community_id)
  
   is_member = community.participants.filter(id=user.id).exists()
   is_requested = community.requests.filter(id=user.id).exists()
   data = {'is_member': is_member, 'is_requested': is_requested}
   #print(data)
  else:
   data = {'is_member': False, 'is_requested': False}
  
  return Response({'data': data ,'message':'OK'},status=status.HTTP_200_OK)
  
 except Exception as e:
  return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
class MyCommunity(APIView):
 #Get Community Posts
 def get(self, request, id: str):

  try:
    data = request.query_params
    post_size = data.get('size', 10)
    filter_type = data.get('filter_type', 'popular') #This is popular and newests
    query_type = data['type']

    user: User = request.user

   # Find the related community
    try:
      community = Community.objects.get(id=id)
    except Community.DoesNotExist:
      return Response({'data':{},'message':'Unable to find community related to this ID'},status=status.HTTP_404_NOT_FOUND)
    
    # Get the community Post
    if query_type == 'post':
     
    #  This is depending on type of post user wants to get
     posts = Posts.objects.filter(community__id=community.id)
     if filter_type == 'popular':
      posts = posts.annotate(likes_count=models.Count('likes')).order_by('likes_count')
      # print(posts)
     elif filter_type == 'newest':
      posts = posts.order_by('-created_at')

      # This will return an error response if the type os not what i specified
     if filter_type not in ['popular', 'newest']:
      return Response({'data':{},'message':'Invalid query'}, status=status.HTTP_404_NOT_FOUND)


     posts = posts[:post_size]
     
     data = PostSerializer(posts, many=True)

     return Response({'data':data.data, 'message':'OK'},status=status.HTTP_200_OK)

    # Get the community Details
    if query_type == 'details':
     data = CommunityDetailsSerializer(community)

     return Response({'data':data.data,'message':'OK'}, status=status.HTTP_200_OK)

    if query_type == 'my_communities':
     try:
      if user.is_authenticated:
      # Get the related community for user
        communities = Community.objects.filter(owner=user).values('id', 'name', 'display_picture')
      
        data = MyCommunities(communities, many=True)

      # we are to return just the 
        return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)
      else:
        return Response({'data':{},'message':'Please login to your account first'}, status=status.HTTP_401_UNAUTHORIZED)
     except Exception as e:
      print(e)
      return Response({'data':{},'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if query_type == 'is_liked':
      post_id = data['post_id']

      post = get_object_or_404(Posts, id=post_id)

      is_liked = post.likes.filter(id=user.id).exists()

      return Response({'data':is_liked, 'message':'OK'},status=status.HTTP_200_OK)

    if query_type == 'comments':
      post_id = data['post_id']
      size = data.get('size', 10)
      post = get_object_or_404(Posts, id=post_id)

      comments = PostComments.objects.filter(post=post).order_by('-created_at')[:int(size)]

      data = PostCommentSerializer(comments, many=True)

      return Response({'data':data.data,'message':'OK'}, status=status.HTTP_200_OK)

    if query_type == 'members':
      from serializers import PartialUserSerializer
      sort_data = data.get('sort', False)
      size = int(data.get('pageParams', 6))
      
      members = community.participants.exclude(username=community.owner).order_by('username' if sort_data else '')[:size]

      data = PartialUserSerializer(members, many=True)

      return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)

    if query_type == 'requests':
      from serializers import PartialUserSerializer
      size = int(data.get('pageParams', 6))
      
      members = community.requests.exclude(username=community.owner)[:size]

      data = PartialUserSerializer(members, many=True)

      return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)
    #  If the query is not matching
    if query_type not in ['post', 'details', 'my_communities', 'is_liked', 'comments','members', 'requests']:
     return Response({'data':{},'message':'Invalid query'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


  except Exception as e:
   return Response({'data':{},'message': str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 # This allow user to post on the community
 @permission_classes([IsAuthenticated])
 def post(self, request, id: str):
        try:
            user = request.user
            data = request.data
            caption = data['caption']
            quiz_id = data.get('quiz_id', '')
            images_length = data.get('images_length', '')

            # Ensure the user is a member of that community
            community = get_object_or_404(Community, id=id)
            community.am_i_a_member(user)

            # Create the new post
            post = Posts(
                posted_by=user,
                caption=caption,
                community=community
            )

            # If the user wants to include a quiz
            if quiz_id:
                try:
                    quiz = get_object_or_404(Quiz, id=quiz_id)
                    post.quiz = quiz
                except Quiz.DoesNotExist:
                    return Response({'data': {}, 'message': 'Quiz with this ID not found'}, status=status.HTTP_404_NOT_FOUND)

            # Save the post before creating related PostImages
            post.save()
            # If the post has images
            for i in range(int(images_length)):
                image_url = image_uploader(image=data[f'image{i}'])

                PostImages.objects.create(image=image_url, post=post)

            return Response({'data': {}, 'message': "OK"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({'data': {}, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
 
 #Edit your post
 @permission_classes([IsAuthenticated])
 def patch(self, request, id: str):
        from base.models import Category
        try:
            user = request.user
            data = request.data


            if data.get('type', '') == 'community':
              allow_categories = data['allow_categories']
              display_picture = data['display_picture']
              join_with_request = data.get('join_with_request', False)

              


              join_with_request = join_with_request.capitalize()
              allow_categories = allow_categories.split(',')

              community = get_object_or_404(Community, id=id)

              community.name = data.get('name', community.name)
              community.join_with_request = join_with_request or community.join_with_request

              categories = Category.objects.filter(body__in=allow_categories)
              community.allow_categories.set(categories or community.allow_categories)

              community.save()

              if display_picture and display_picture != 'undefined':
                image = image_uploader(display_picture) #Upload image to server -->Return a URL
                community.display_picture = image
                community.save()



              return Response({'data':{},'message':'Community Editted Successfully'})

            post_id = data.get('post_id')
            quiz_id = data.get('quiz_id', '')
            images_to_update_len = data.get('images_to_update_len', 0)
            more_images = data.get('more_images_len', 0)
            images_to_remove_len = data.get('images_to_remove_len', 0)

            post = get_object_or_404(Posts, id=post_id)
            
            post_owner(post=post, user=user)

            with transaction.atomic():
                # Handle quiz
                if quiz_id:
                    quiz = get_object_or_404(Quiz, id=quiz_id)
                    post.quiz = quiz
                else:
                    post.quiz = None

                post.save()

                # Handle images to update
                for i in range(int(images_to_update_len)):
                    old_image_key = f'old_image_{i}'
                    new_image_key = f'new_image_{i}'
                    
                    if old_image_key in data and new_image_key in data:
                        old_image_url = data[old_image_key]
                        new_image_url = image_uploader(data[new_image_key])

                        post_images = PostImages.objects.filter(image=old_image_url)
                        
                        if post_images.exists():
                            post_images.update(image=new_image_url)

                # Handle more images
                for i in range(int(more_images)):
                    new_image_key = f'add_image_{i}'
                    
                    if new_image_key in data:
                        image_url = image_uploader(data[new_image_key])
                        PostImages.objects.create(image=image_url, post=post)
                
                post_images = PostImages.objects.filter(post=post)

                # Remove img if not needed 
                for i in range(int(images_to_remove_len)):
                  image_key = f'remove_img_{i}'

                  if image_key in data:
                    post_images.get(image=data[image_key]).delete()
                    remove_image_path(data[image_key])

                # Update caption
                post.caption = data.get('caption', post.caption)
                post.save()

            return Response({'data': {}, 'message': 'Post updated successfully'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


 #Delete Post on Community -->If you are the on that posted it
 @permission_classes([IsAuthenticated])
 def delete(self, request, id: str):
  try:
    user:User = request.user
    data = request.query_params

   

    if data.get('type', '') == 'members':
      user_id = data['user_id']
      username = data['username']

      community = get_object_or_404(Community, id=id)

      user = community.participants.get(id=user_id, username=username)

      community.participants.remove(user)
      return Response({'data':{},'message':'User removed'},status=status.HTTP_200_OK)
    else:
      post = get_object_or_404(Posts, id=id)
      post_owner(post=post, user=user) #If user is the owner this will pass
      post.delete()
    return Response({'data':{},'message':'Deleted'},status=status.HTTP_200_OK)
  except Exception as e:
    return Response({'data':{},'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def community_action(request, post_id: str):
  try:
    user: User = request.user
    data = request.data
    # First locate the post
    post = get_object_or_404(Posts, id=post_id)

    if data['type'] == 'like':
      data = post.likes.filter(id=user.id)

      if data.exists():
        post.likes.remove(user)
      else:
        post.likes.add(user)

      return Response({'data':{},'message':'OK'}, status=status.HTTP_200_OK)

    if data['type'] == 'comment':
      body = data['comment']

        # Create a new comment and save it to the database
      new_comment = PostComments(body=body, post=post, user=user)
      new_comment.save()

      data = PostCommentSerializer(new_comment)


      return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)



    if data['type'] not in ['like', 'comment']:
      return Response({'data':{},'message':'Invalid query action'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # If user is like post already unlike it
    

  except Exception as e:
    return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_community(request):
 from base.models import Category
 try:
  user: User = request.user

  data = request.data
  name = data['name']
  allow_categories = data["allow_categories"]
  description = data.get('description', '')
  display_picture = data.get('display_image')
  join_with_request = data.get('join_with_request', False)

  allow_categories = allow_categories.split(',')
  join_with_request = join_with_request.capitalize()

  Community.check_for_user_communities(user=user, name=name) #This will check if the user has too many communities or if the community with this name already exists.


  image = image_uploader(display_picture) #Upload image to server -->Return a URL

  community = Community(
   name=name,
   owner=user,
   description=description, 
   join_with_request=join_with_request,
   display_picture = image
  )

  # # Find the category and add it.
  categories = Category.objects.filter(body__in=allow_categories)
  # community.save()
  community.allow_categories.set(categories)
  
  community.participants.add(user)
  
  community.save()

  return Response({'data':{},"message":'OK'},status=status.HTTP_200_OK)
 except Exception as e:
  return Response({'data':{},"message":str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def search_community(request, id: str):
  from serializers import PartialUserSerializer
  try:
    search_keyword = request.query_params.get('search', '')
    community = get_object_or_404(Community, id=id)

    # User can find post and related user with the search keyword
    posts = Posts.objects.filter(community=community).filter(
      Q(caption__icontains=search_keyword) | Q(posted_by__username__icontains=search_keyword) | Q(quiz__title__icontains=search_keyword)
    ).order_by('-created_at')[:12]

    data = {
      'post': [],
      'members': []
    }

    if not search_keyword:
      return Response({'data':data,'message':'OK'},status=status.HTTP_200_OK)

    # Finds members
    members = community.participants.filter(
      Q(id__icontains=search_keyword) | Q(username__icontains=search_keyword) | Q(email__icontains=search_keyword)
    )[:12]

    post_serializer = PostSerializer(posts, many=True)
    member_serializer = PartialUserSerializer(members, many=True)

    data['post'] = post_serializer.data
    data['members'] = member_serializer.data

    return Response({'data':data,'message':'OK'},status=status.HTTP_200_OK)

  except Exception as e:
    return Response({'data':{},'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_or_accept_request(request, id: str):
    from base.helpers import notification_helper
    from base.models import Notifications
    try:
        data = request.data
        user: User = request.user
        community = get_object_or_404(Community, id=id)
        community.is_community_owner(user)

        type = data['type']
        user_id = data['user_id']


        if type == 'accept_all':
          users = community.requests.all()

          for i in users:
            community.accept_request(i.id)

          return Response({'data':{},'message':'OK'},status=status.HTTP_200_OK)



        if type == 'accept':
          community.accept_request(user_id)
          print(user_id, 'User')
          notification_helper(user, f'Congratulations you have been accepted to {community.name}', Notifications.NotificationType.DEFAULT, '', '')



        if type == 'reject':
          community.reject_request(user_id)


        if type not in ['accept', 'reject']:
          return Response({'data':{},'message':'Action does not exist'})
        
        return Response({'data':{},'message':'OK'},status=status.HTTP_200_OK)
        

    except Exception as e:
        return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)




