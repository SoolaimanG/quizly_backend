
import uuid
from datetime import timedelta
from django.utils import timezone

from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.translation import gettext as _
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


from .helpers import upload_to, send_email



# Create your models here.
class UserManager(UserManager):
    
    def edit_user_profile(self, username):
        return username


#Basic App Models
class User(AbstractUser):
 
 class AccountType(models.TextChoices):
  STUDENT = 'S', _('student'),
  TEACHER = 'T', _('teacher'),
 
 class AuthType(models.TextChoices):
  LOCAL = 'L', _('local'),
  GOOGLE = 'G', _('google'),
  TWITTER = 'T',_('twitter'),
 
 account_type = models.CharField(
  choices=AccountType.choices,
  default=AccountType.STUDENT,
  max_length=20
 )
 age = models.IntegerField(null=True,blank=True)
 auth_provider = models.CharField(
  choices=AuthType.choices,
  default=AuthType.LOCAL,
  max_length=30
 )
 bio = models.TextField(max_length=255,null=True,blank=True)
 email = models.EmailField(max_length=100, unique=True, error_messages="User with this email already exists")
 id = models.UUIDField(unique=True,default=uuid.uuid4, primary_key=True)
 profile_image = models.URLField(null=True, blank=True)
 username = models.CharField(unique=True,max_length=100, error_messages="User with this username already exists")
 first_time_login = models.BooleanField(default=True)
 email_verified = models.BooleanField(default=False)
 signup_complete = models.BooleanField(default=False)
 
#  Check if the email has been tempered with.
 def check_email_status(self):
     user: User = User.objects.get(id=self.id)
     same_email = self.email == user.email
     if not same_email:
         self.email_verified = False
 objects = UserManager()
 
 def can_post_quiz(self):
     return bool(self.account_type == 'T')
 
 def signup_is_complete(self):
     is_signup_complete = all([self.first_name, self.last_name, self.age, self.email_verified])
     self.signup_complete = is_signup_complete
 
 def validate_email(self):
     try:
        validator = EmailValidator(message='Please use a valid email address. Thank you')
        validator(self.email)
     except Exception as e:
        raise ValidationError(str(e))
    
 def make_sure_user_has_single_account(self):
     if self.account_type == self.AccountType.STUDENT:
        tutor = TeachersAccount.objects.filter(user__id=self.id).first()
        if tutor: tutor.delete()
     
     if self.account_type == self.AccountType.TEACHER:
        student = StudentAccount.objects.filter(user__id=self.id).first()
        if student: student.delete()
 
 def save(self, *arg, **kwarg):
     self.validate_email()
     self.check_email_status()
     self.signup_is_complete()
     self.make_sure_user_has_single_account()
     super().save(*arg, **kwarg)
     
 
 def __str__(self) -> str:
    return self.username

class ForgetPassword(models.Model):
    
    
    expires_by = models.DateTimeField(default=timezone.now() + timedelta(minutes=25))
    id = models.UUIDField(unique=True, default=uuid.uuid4, primary_key=True)
    number_of_request = models.IntegerField(default=1)
    otp = models.CharField(max_length=5)
    requested_by = models.ForeignKey('base.User', on_delete=models.CASCADE)
    next_request = models.DateTimeField(default=timezone.now() + timedelta(seconds=30))
    
    def __str__(self) -> str:
        return self.otp
    
class EmailVerification(models.Model):
    user = models.ForeignKey('base.User', on_delete=models.CASCADE)
    expires = models.DateTimeField(default=timezone.now() + timedelta(minutes=25))
    verify_token = models.UUIDField(default=uuid.uuid4,null=False, unique=True)
    number_of_requests = models.IntegerField(default=1)
    next_request = models.DateTimeField(default=timezone.now() + timedelta(minutes=10))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    def __str__(self) -> str:
        return self.user.email

class Category(models.Model):
    body = models.CharField(max_length=50, default="", unique=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    
    def __str__(self) -> str:
       return self.body[:30]
    
class StudentAccount(models.Model):
    
    class QuizDifficulty(models.TextChoices):
        ALL = 'all',_('All'),
        EASY = 'easy',_('EASY'),
        MEDIUM = 'medium',_('Medium'),
        HARD = 'hard',_('Hard')
    
    favourites = models.ManyToManyField('base.Category', blank=True)
    user = models.ForeignKey('base.User', on_delete=models.CASCADE)
    streaks_count = models.IntegerField(null=True, blank=True)
    id = models.UUIDField(primary_key=True,default=uuid.uuid4)
    difficulty=models.CharField(choices=QuizDifficulty.choices, max_length=10, default=QuizDifficulty.MEDIUM)
    xp = models.IntegerField(default=0)
    my_teachers = models.ManyToManyField('base.TeachersAccount', blank=True, related_name='user_teachers')
    
    def __str__(self) -> str:
       return self.user.username
   
class TeachersAccount(models.Model):
    
    class Education_level(models.TextChoices):
     MASTERS= "masters", _("MASTERS"),
     DOCTORATE= "doctorate", _("DOCTORATE"),
     BACHELOR = 'bachelor', _("BACHELOR"),
    
    user = models.ForeignKey('base.User',on_delete=models.CASCADE)
    rating = models.FloatField(default=0.5)
    students = models.ManyToManyField('base.StudentAccount', blank=True, related_name='my_students')
    quizzes = models.ManyToManyField('quiz.Quiz', blank=True)
    specializations = models.ManyToManyField('base.Category', blank=True)
    educational_level = models.TextField(choices=Education_level.choices, default=Education_level.BACHELOR, max_length=15)
    phone_num = models.CharField(max_length=15, null=True, blank=True)
    whatsapp_link = models.URLField(null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    
    def can_use_ai(self):
        return False
    
    def __str__(self) -> str:
       return self.user.username
    
class Logs(models.Model):
    statement = models.TextField(max_length=150, null=True, blank=True)
    user = models.ForeignKey('base.User', on_delete=models.CASCADE)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self) -> str:
       return self.statement[:50]
    
class UploadImage(models.Model):
   image = models.ImageField(upload_to=upload_to)

   def __str__(self):
      return self.image.url
   
class Notifications(models.Model):
   class NotificationType(models.TextChoices):
      DEFAULT = 'default', _('DEFAULT')
      COMMUNITY_REQUEST = 'community_request', _('COMMUNITY_REQUEST')
      NEW_QUIZ_ALERT = 'new_quiz_alert', _('NEW_QUIZ_ALERT')
      ACHIEVEMENT = 'achievement', _('ACHIEVEMENT')

   id = models.UUIDField(default=uuid.uuid4, primary_key=True)
   message = models.CharField(max_length=500)
   path = models.URLField(null=True, blank=True)
   user = models.ForeignKey(User, on_delete=models.CASCADE)
   notification_type = models.CharField(choices=NotificationType.choices, default=NotificationType.DEFAULT, max_length=30)
   is_read = models.BooleanField(default=False)
   quiz=models.ForeignKey('quiz.Quiz', on_delete=models.CASCADE, null=True, blank=True, related_name='quiz')
   user_requesting = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='user_requesting')


   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def before_saving_check(self):
      if self.notification_type == self.NotificationType.DEFAULT and not self.message:
         raise ValueError('Message is required')
      
      if self.notification_type == self.NotificationType.NEW_QUIZ_ALERT and not all([self.quiz, self.path]):
         raise ValueError('Quiz and path are required')
      
      if self.notification_type == self.NotificationType.COMMUNITY_REQUEST and not self.user_requesting:
         raise ValueError('User that request is required')
      
   def save(self, *arg, **kwarg):
        self.before_saving_check()
        super().save(*arg, **kwarg)
      
class FeatureWaitList(models.Model):
    
    class Features(models.TextChoices):
        IMAGE_FILTER = 'IMAGE_FILTER', _('IMAGE_FILTER')
        AI_HELP = 'AI_HELP', _('AI_HELP')
        QuestionGroup = "QuestionGroup", _("QuestionGroup")
        Time = "Time",_('Time')
        SET_RESPONSE_LIMIT = 'SET_RESPONSE_LIMIT',_('SET_RESPONSE_LIMIT')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feature_name = models.CharField(max_length=50, choices=Features.choices)
    
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Functions to call
    # Send Emails to users waiting for the update
    
    # Check if user is already on the wait-list
    def check_user(self):
        print(self.feature_name)
        if FeatureWaitList.objects.filter(
            Q(user__id=self.user.id) & 
            Q(feature_name=self.feature_name)
        ).exists():
            raise ValidationError('You already joined the wait-list, you will be informed when this feature is available.')
        
        # Restricted to only super users.
    def send_emails_to_users_on_waitList(self, feature_name: str, super_user: User | None):
        
        if super_user is None or super_user.is_superuser:
            raise ValueError('Sorry! you can not access this endpoint. Its only available to Super Users')
        
        users_on_wait_list = FeatureWaitList.objects.filter(feature_name=feature_name).values_list('user__email')
        
        try:
            send_email(
            subject='Hooray! New Feature is available on Quizly.',
            body='',
            recipients=users_on_wait_list
            )
        except Exception as e:
            raise str(e)
        
    def save(self, *arg, **kwarg):
        self.check_user()
        super().save(*arg, **kwarg)

