
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
    quizzes = models.ManyToManyField('base.Quiz', blank=True)
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
    
class Quiz(models.Model):
    
 class ResultDisplayType(models.TextChoices):
     ON_SUBMIT = 'on_submit', _('ON_SUBMIT'),
     ON_COMPLETE = 'on_complete', _('ON_COMPLETE'),
     MARK_BY_TEACHER = 'mark_by_teacher',_('MARK_BY_TEACHER'),
     
 class Difficulty(models.TextChoices):
     EASY = 'easy', _('EASY'),
     MEDIUM = 'medium', _('MEDIUM'),
     HARD = 'hard',_('HARD'),
     
 class ALLOWEDUSERS(models.TextChoices):
     AUTHENTICATED_USERS = 'authenticated_users', _('AUTHENTICATED_USERS'),
     ONLY_MY_STUDENTS = 'only_my_students', _('ONLY_MY_STUDENTS'),
     ALL = 'all',_('ALL'),
 
 access_with_key = models.BooleanField(default=False)
 category = models.ForeignKey('base.Category', null=True, on_delete=models.CASCADE)
 created_at = models.DateTimeField(auto_now=True)
 descriptions = models.TextField(max_length=2000, default='Nothing to see')
 difficulty = models.TextField(choices=Difficulty.choices,default=Difficulty.MEDIUM, max_length=10)
 time_limit = models.PositiveIntegerField(default=0)
 host = models.ForeignKey('base.TeachersAccount', on_delete=models.CASCADE, default=None)
 id=models.UUIDField(primary_key=True,default=uuid.uuid4)
 participants = models.ManyToManyField('base.StudentAccount',blank=True)
 requirements= models.TextField(max_length=2000, default='Nothing to see')
 banner = models.URLField(null=True, blank=True)
 title= models.CharField(max_length=100, blank=True,null=True)
 rating= models.FloatField(default=0.0)
 submit_on_leave = models.BooleanField(default=False)
 allow_calculator= models.BooleanField(default=False)
 allow_word_search= models.BooleanField(default=False)
 allow_robot_read=models.BooleanField(default=False)
 instructions = models.TextField(max_length=3000, default='Nothing to see')
 result_display_type = models.TextField(choices=ResultDisplayType.choices, max_length=20, default=ResultDisplayType.ON_COMPLETE)
 allow_retake = models.BooleanField(default=False, null=True, blank=True)
 finish_message = models.CharField(max_length=200, null=True, blank=True)
 allowed_users = models.TextField(choices=ALLOWEDUSERS.choices,max_length=20,default=ALLOWEDUSERS.ALL)
 
 def __str__(self):
     return self.title

class Question(models.Model):
 
 class QuestionTypes(models.TextChoices):
  TRUE_OR_FALSE = 'true_or_false', _('TRUE_OR_FALSE')
  OBJECTIVE = 'objective', _('OBJECTIVE')
  GERMAN = 'german', _('GERMAN')
  MULTIPLE_CHOICES = 'multiple_choices', _('MULTIPLE_CHOICES')
 
 question_type = models.TextField(choices=QuestionTypes.choices,default=QuestionTypes.OBJECTIVE)
 quiz_id = models.ForeignKey('base.Quiz', on_delete=models.CASCADE)
 answer_is_true = models.BooleanField(default=False)
 answer = models.TextField(max_length=255,null=True,blank=True)
 is_compulsary = models.BooleanField(default=False)
 question_point = models.PositiveIntegerField(default=5)
 correct_answer_explanation = models.CharField(max_length=300)
 incorrect_answer_penalty= models.PositiveIntegerField(default=5)
 hint = models.TextField(max_length=250, null=True, blank=True, default='No available hint.')
 question_number = models.PositiveIntegerField(default=1)
 id = models.UUIDField(primary_key=True, default=uuid.uuid4)
 question_body = models.TextField(max_length=400, default=None)
 question_image = models.URLField(null=True, blank=True)
 mistakes_to_ignore = models.IntegerField(default=0)
 is_strict = models.BooleanField(default=True)

 #Perform this checks before adding question for teacher.
 def additional_checks(self):
    quiz = Quiz.objects.get(id=self.quiz_id.id)

    # # Find all the related questions 
    questions = Question.objects.filter(quiz_id__id=self.quiz_id.id).count()

    if self.question_number == 0 : self.question_number = questions + 1 #Automatically count the numbers of question to show to users

    # Check if the question is a boolean question and its its stricts
    if(
       self.question_type == self.QuestionTypes.TRUE_OR_FALSE and self.mistakes_to_ignore > 0
    ):
       self.is_strict = False

    # If the quiz if mark on check then make sure the answers and correct answer explanation is set
    if( 
       quiz.result_display_type == quiz.ResultDisplayType.ON_COMPLETE and self.question_type == self.QuestionTypes.GERMAN and not self.answer
    ):
       raise ValidationError('Provide answer for this question.')



 def save(self, *arg, **kwarg):
    self.additional_checks()
    super().save(*arg, **kwarg)
 
 def __str__(self):
  return self.question_body
 
class GermanOptions(models.Model):
 is_strict = models.BooleanField(default=False)
 mistakes_to_ignore = models.IntegerField(default=1)
 belongs_to = models.ForeignKey(Question, on_delete=models.CASCADE,db_column='belongs_to_id',default=None) 
 
class ObjectiveOptions(models.Model):
 body = models.TextField(null=True, blank=True, max_length=200)
 is_correct_answer = models.BooleanField(default=False)
 image_url = models.URLField(null=True, blank=True)
 belongs_to = models.ForeignKey('base.Question',on_delete=models.CASCADE,db_column='belongs_to_id',default=None) 
 
 def __str__(self):
  return self.belongs_to.quiz_id.title

class Comments(models.Model):
    user = models.ForeignKey('base.User', on_delete=models.CASCADE)
    body = models.CharField(max_length=300)
    quiz= models.ForeignKey('base.Quiz', on_delete=models.CASCADE)
    likes = models.ManyToManyField(User, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.body[:50]

class AttemptedQuizOfUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    last_accessed_time = models.DateTimeField(auto_now=True, null=True,blank=True)
    is_completed = models.BooleanField(default=False)
    questions_answered_by_student = models.ManyToManyField('base.Question', related_name='attempted_quizzes') 
    current_question_index = models.PositiveIntegerField(default=0)
    attempted_by = models.ForeignKey(StudentAccount, on_delete=models.CASCADE,default=None)
    answers = models.JSONField(default=list, null=True, blank=True)
    XP = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    
    def __str__(self):
        return self.attempted_by.user.username + ' answered ' + self.quiz.title

class AnonymousUser(models.Model):
    anonymous_id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    xp = models.PositiveIntegerField(default=10)
    completed_quiz = models.ManyToManyField(Quiz, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self) -> None:
       return str(self.anonymous_id)
    
class AttemptedQuizByAnonymousUser(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempted_by = models.ForeignKey(AnonymousUser, on_delete=models.CASCADE)
    xp_earn = models.PositiveIntegerField(default=0)

    def prevent_duplicate(self):
        if AttemptedQuizByAnonymousUser.objects.filter(
            Q(question=self.question) & Q(attempted_by=self.attempted_by) & Q(quiz=self.quiz)
        ).count() > 1:
            raise ValidationError('Duplicate question for user found')

    def save(self, *args, **kwargs):
        self.prevent_duplicate()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.quiz.title

class QuizAccessToken(models.Model):
    quiz = models.ForeignKey('base.Quiz', on_delete=models.CASCADE)
    access_token = models.CharField(max_length=20)
    should_expire = models.BooleanField(default=False)
    expiration_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    number_of_usage = models.PositiveIntegerField(default=50)
    usage = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.access_token

class ScoreBoard(models.Model):
    user = models.ForeignKey('base.StudentAccount', on_delete=models.CASCADE)
    quiz = models.ForeignKey('base.Quiz', on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)
    xp_earn = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    corrections = models.JSONField(default=list, null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    attempted_question = models.PositiveIntegerField(default=0)
    feedback = models.TextField(null=True, blank=True)
    total_question = models.PositiveIntegerField(null=True, blank=True)
    expected_xp = models.PositiveIntegerField(default=0)
    
    def __str__(self) -> str:
       return self.user.user.username

class UploadImage(models.Model):
   image = models.ImageField(upload_to=upload_to)

   def __str__(self):
      return self.image.url
   
class SavedQuiz(models.Model):
   quiz = models.ForeignKey("base.Quiz", on_delete=models.CASCADE)
   user = models.ForeignKey("base.User", on_delete=models.CASCADE)

   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)


   def __str__(self):
      return self.quiz.title

class Ratings(models.Model):
   
   class RatingsType(models.TextChoices):
      TEACHER = 'teacher', _('TEACHER')
      Quiz = 'quiz', _('QUIZ')

   teacher = models.ForeignKey(TeachersAccount, on_delete=models.CASCADE, null=True, blank=True)
   quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True)
   user = models.ForeignKey(User, on_delete=models.CASCADE)
   type = models.TextField(choices=RatingsType.choices, default=RatingsType.Quiz, max_length=10)

   def checks(self):
      if self.type == Ratings.RatingsType.Quiz and not self.quiz:
         raise ValidationError("Quiz is required.")
      
      if self.type == Ratings.RatingsType.TEACHER and not self.teacher:
         raise ValidationError("Teacher to rate is required.")
      
   def save(self, *arg, **kwarg):
      self.checks()
      super().save(*arg, **kwarg)

class QuizReports(models.Model):
   user = models.ForeignKey(User, on_delete=models.CASCADE)
   issue = models.TextField(max_length=250)
   quiz= models.ForeignKey(Quiz, on_delete=models.CASCADE)
   question = models.ForeignKey(Question, on_delete=models.CASCADE)
   created_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
      return self.issue[:50]

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
   quiz=models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True, related_name='quiz')
   user_requesting = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='user_requesting')


   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)

   def checkings(self):
      if self.notification_type == self.NotificationType.DEFAULT and not self.message:
         raise ValueError('Message is required')
      
      if self.notification_type == self.NotificationType.NEW_QUIZ_ALERT and not all([self.quiz, self.path]):
         raise ValueError('Quiz and path are required')
      
      if self.notification_type == self.NotificationType.COMMUNITY_REQUEST and not self.user_requesting:
         raise ValueError('User that request is required')
      
   def save(self, *arg, **kwarg):
        self.checkings()
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

