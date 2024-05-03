from rest_framework import serializers
from base.models import ForgetPassword, Category, TeachersAccount, StudentAccount, Notifications, User

from quiz.models import Quiz

class UserSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    first_time_login = serializers.BooleanField()
    last_login = serializers.DateTimeField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    id = serializers.UUIDField()
    is_active = serializers.BooleanField()
    email_verified = serializers.BooleanField()
    signup_complete = serializers.BooleanField()
    auth_provider = serializers.CharField()
    account_type = serializers.CharField()
    profile_image = serializers.ImageField()
    date_joined = serializers.DateTimeField()
    bio = serializers.CharField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data
  
class ForgetPasswordSerializer(serializers.ModelSerializer):
 
 class Meta:
   model = ForgetPassword
   fields = ['expires_by']
class CategorySerializer(serializers.ModelSerializer):
  class Meta:
    model = Category
    fields = ['body']
class TeachersAccountSerializer(serializers.ModelSerializer):
    specializations = CategorySerializer(read_only=True, many=True)
    class Meta:
        model = TeachersAccount
        fields = '__all__'
class HostDetails(serializers.ModelSerializer):
    profile_image = serializers.ImageField(source='user.profile_image', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    bio = serializers.CharField(source='user.bio')

    class Meta:
        model = TeachersAccount
        fields = ['profile_image', 'username', 'user_id', 'bio','phone_num']
class UUIDListSerializer(serializers.Serializer):
    uuids = serializers.ListField(child=serializers.UUIDField())
class ImageSerializer(serializers.Serializer):
   image = serializers.ImageField()
class PartialUserSerializer(serializers.ModelSerializer):
   username = serializers.CharField()
   profile_image = serializers.URLField( required=False)
   id = serializers.UUIDField()

   class Meta:
      model = User
      fields = ['profile_image', 'username', 'id', 'account_type']
class PartialQuizSerializer(serializers.ModelSerializer):
   title = serializers.CharField()
   banner = serializers.URLField(required=False)
   id = serializers.UUIDField()
   host = HostDetails(read_only=True)

   class Meta:
      model = Quiz
      fields = ['title', 'banner', 'id', 'host']

class NotificationSerializer(serializers.ModelSerializer):
   
  #  user = PartialUserSerializer(read_only=True)
   user_requesting = PartialUserSerializer(read_only=True)
  #  quiz = PartialQuizSerializer(read_only=True)
   
   class Meta:
      fields = '__all__'
      model = Notifications
class StudentAccountSerializer(serializers.ModelSerializer):
  user = PartialUserSerializer(read_only=True)
  favourites = CategorySerializer(read_only=True, many=True)
  class Meta:
    model = StudentAccount
    fields = '__all__'
  
  

  
  