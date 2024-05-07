from dotenv import load_dotenv
load_dotenv()

from django.db import models
from uuid import uuid4
from datetime import datetime, timedelta
import os
from typing import List

from base.models import User, StudentAccount, TeachersAccount

from django.utils.translation import gettext as _
# from django.db.models import BaseManager, Q, F
from django.core.exceptions import ValidationError
from django.db.models import Q, F

from base.helpers import send_email
from emails import report_emails

# Model Managers
class QuizScoreBoardManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().order_by('-xp_earn')
       
# TODO: 
class UserResponseManager(models.Manager):
    pass


class Quiz(models.Model):
    
 class ResultDisplayType(models.TextChoices):
     ON_SUBMIT = 'on_submit', _('ON_SUBMIT'),
     ON_COMPLETE = 'on_complete', _('ON_COMPLETE'),
     MARK_BY_TEACHER = 'mark_by_teacher',_('MARK_BY_TEACHER'),
     
 class Difficulty(models.TextChoices):
     EASY = 'easy', _('EASY'),
     MEDIUM = 'medium', _('MEDIUM'),
     HARD = 'hard',_('HARD'),
     
 class UsersToParticipate(models.TextChoices):
     AUTHENTICATED_USERS = 'authenticated_users', _('AUTHENTICATED_USERS'),
     ONLY_MY_STUDENTS = 'only_my_students', _('ONLY_MY_STUDENTS'),
     ALL = 'all',_('ALL'),
 
 access_with_key = models.BooleanField(default=False)
 category = models.ForeignKey('base.Category', null=True, on_delete=models.CASCADE)
 created_at = models.DateTimeField(auto_now=True)
 descriptions = models.TextField(max_length=2000, default='Nothing to see')
 difficulty = models.TextField(choices=Difficulty.choices,default=Difficulty.MEDIUM, max_length=10)
 time_limit = models.PositiveIntegerField(default=0)
 id=models.UUIDField(primary_key=True,default=uuid4)
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
 allowed_users = models.TextField(choices=UsersToParticipate.choices,max_length=20,default=UsersToParticipate.ALL)
 expected_xp = models.PositiveIntegerField(default=0)
 is_published = models.BooleanField(default=False)
 
#  If the content is AI generated content or created by a user
 host = models.ForeignKey(TeachersAccount, on_delete=models.CASCADE, null=True, blank=True)
 is_ai_generated = models.BooleanField(default=False)
 
 def __str__(self):
     return self.title

class Question(models.Model):
 
 class QuestionTypes(models.TextChoices):
  TRUE_OR_FALSE = 'true_or_false', _('TRUE_OR_FALSE')
  OBJECTIVE = 'objective', _('OBJECTIVE')
  OPEN_ENDED = 'open_ended', _('OPEN_ENDED')
  MULTIPLE_CHOICES = 'multiple_choices', _('MULTIPLE_CHOICES')
 
 question_type = models.TextField(choices=QuestionTypes.choices,default=QuestionTypes.OBJECTIVE)
 quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
 true_or_false = models.BooleanField(default=False)
 answer = models.TextField(max_length=255,null=True,blank=True)
 is_compulsory = models.BooleanField(default=False)
 question_point = models.PositiveIntegerField(default=5)
 correct_answer_explanation = models.CharField(max_length=300)
 incorrect_answer_penalty= models.PositiveIntegerField(default=5)
 hint = models.TextField(max_length=250, null=True, blank=True, default='No available hint.')
 question_number = models.PositiveIntegerField(default=1)
 id = models.UUIDField(primary_key=True, default=uuid4)
 question_body = models.TextField(max_length=400, default=None)
 question_image = models.URLField(null=True, blank=True)
 mistakes_to_ignore = models.IntegerField(default=0)

 #Perform this checks before adding question for teacher.
 def additional_checks(self):
    # Check if the question is a boolean question and if its strict
    if(
       self.question_type == self.QuestionTypes.TRUE_OR_FALSE and self.mistakes_to_ignore > 0
    ):
       self.is_strict = False

    # If the quiz if mark on check then make sure the answers and correct answer explanation is set
    if( 
       self.quiz.result_display_type == self.quiz.ResultDisplayType.ON_COMPLETE and self.question_type == self.QuestionTypes.OPEN_ENDED and not self.answer
    ):
       raise ValueError('Provide answer for this question.')

 def calculate_expected_xp(self):
     expected_xp = Question.objects.filter(quiz=self.quiz).aggregate(expected_exp=models.Sum('question_point')).values('expected_xp') or 0
     self.quiz.expected_xp = expected_xp
     self.quiz.save()

 def save(self, *arg, **kwarg):
    self.additional_checks()
    super().save(*arg, **kwarg)
 
 def __str__(self):
  return self.question_body

class QuizComments(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    body = models.CharField(max_length=300)
    quiz= models.ForeignKey(Quiz, on_delete=models.CASCADE)
    likes = models.ManyToManyField(User, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Making sure the quiz does not contain profanity.
    def save(self, *arg, **kwarg):
        super().save(*arg, **kwarg)

    def __str__(self):
        return self.body[:50]
    
class OpenEndedOption(models.Model):
    is_strict = models.BooleanField(default=False)
    mistakes_to_ignore = models.IntegerField(default=1)
    question = models.ForeignKey(Question, on_delete=models.CASCADE,db_column='belongs_to_id',default=None) 

class MultipleChoiceOption(models.Model):
    body = models.TextField(null=True, blank=True, max_length=200)
    is_correct_answer = models.BooleanField(default=False)
    image_url = models.URLField(null=True, blank=True)
    question = models.ForeignKey(Question,on_delete=models.CASCADE) 
 
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    def __str__(self):
        return self.question.quiz.title
    
class QuizzesAttemptedByUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    questions_attempted = models.ManyToManyField(Question, related_name='attempted_questions')
    student = models.ForeignKey(StudentAccount, on_delete=models.CASCADE,default=None)
    xp_earn = models.IntegerField(default=0)
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Modal Object
    objects = QuizScoreBoardManager()
    
    
    def __str__(self):
        return f"{self.student.user.username} attempted {self.quiz.title}"

class UserAnswerForQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_id = models.UUIDField()
    answer = models.JSONField(default=list)
    
    
    def __str__(self) -> str:
       return str(self.user_id)

class AnonymousUser(models.Model):
    anonymous_id = models.UUIDField(default=uuid4, primary_key=True)
    xp = models.PositiveIntegerField(default=10)
    completed_quiz = models.ManyToManyField(Quiz, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    
    # This provides a link between anonymous user and authenticated user
    def link_anonymous_user_to_authenticated_user(self, user:User, quiz: Quiz):
        
        student, student_created = StudentAccount.objects.get_or_create(user__id=user.id, defaults={
            'user':user,
            'xp': self.xp,
        })
        
        if not student_created:
            student.xp=+self.xp
            student.save()
        
        quizzes: List[Quiz] = self.completed_quiz
        attempted_questions_ids = AttemptedQuizByAnonymousUser.objects.filter(quiz__id=quiz.id, anonymous_user=self).values_list('question__id', flat=True)
        questions = Question.objects.filter(quiz=quiz).all()
        questions_completed = questions.filter(id__in=attempted_questions_ids).all()
        
        
        for i in quizzes:
            quiz, quiz_created = QuizzesAttemptedByUser.objects.get_or_create(student__user__id=user.id, defaults={
            'student': student,
            'quiz': i,
            'is_completed': questions.count() == questions_completed,
            'questions_completed': questions_completed,
            })
            
            if not quiz_created:
                quiz.questions_attempted = questions
                quiz.is_completed = True
                
                quiz.save()
        
        self.delete()
    
    def __str__(self) -> None:
       return str(self.anonymous_id)

class AttemptedQuizByAnonymousUser(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    questions_attempted = models.ManyToManyField(Question, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    user_answer = models.CharField(max_length=300, null=True, blank=True)
    anonymous_user = models.ForeignKey(AnonymousUser, on_delete=models.CASCADE)
    xp_earn = models.PositiveIntegerField(default=0)
    
    end_time = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.quiz.title

class QuizAccessToken(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=20)
    expiration_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    max_usage = models.PositiveIntegerField(default=50)
    updated_at = models.DateTimeField(auto_now=True)
    users = models.JSONField(default=list)
    
    
    def check_usage(self):
        if len(self.users) >= self.max_usage:
            raise ValueError("Access token has reached it's max usage")
        
    def add_user(self, user_id: str):
        if user_id not in self.users:
            self.check_usage()
            
            self.users = list(self.users).append(user_id)
            self.save()
            
    def verify_user(self, user_id: str):
        if user_id not in list(self.users):
            raise ValueError('Access token is required to access this quiz')
        
    def save(self, *arg, **kwarg):
        self.check_usage()
        super().save(*arg, **kwarg)
    
    def __str__(self):
        return self.access_token

class QuizScoreBoard(models.Model):
    user = models.ForeignKey(StudentAccount, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    corrections = models.JSONField(default=list, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    questions_answered = models.PositiveIntegerField(default=0)
    xp_earn = models.PositiveIntegerField(default=0)
    expected_xp = models.PositiveIntegerField(default=0)
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    objects = QuizScoreBoardManager()
    

    def __str__(self) -> str:
       return self.user.user.username

class QuizSavedByUser(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    user = models.ForeignKey(StudentAccount, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
      return self.quiz.title

class ReportsOnQuiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report = models.TextField(max_length=250)
    quiz= models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
   
    notification_sent_to_host = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
   
    def check_if_user_has_reported_already(self):
        if ReportsOnQuiz.objects.filter(user=self.user, quiz=self.quiz, question=self.question).exists():
            raise ValueError('Thank you for letting us know there is an issue with this question. We will notify the host of this quiz immediately')
   # Notify the host if the issue has persist
    def notify_host_on_issue(self):
        all_participants = QuizzesAttemptedByUser.objects.filter(quiz=self.quiz).count()
        users_that_report_quiz = ReportsOnQuiz.objects.filter(quiz=self.quiz).count()
        last_email_sent = ReportsOnQuiz.objects.filter(quiz=self.quiz).order_by('-notification_sent_to_host').first()
    
    # Calculate the threshold date for sending a new email (2 days ago)
        threshold_date = datetime.now() - timedelta(days=2)
    
        developers_email = ['Soolaimangee@gmail.com', 'Suleimaangee@gmail.com', 'Suleimangee@gmail.com']
    
        if users_that_report_quiz >= all_participants * 0.6:
        # Check if the last email was sent more than 2 days ago
            if last_email_sent is None or last_email_sent.notification_sent_to_host < threshold_date:
            # Send an email to the host
                path = os.environ.get('QUIZLY_CLIENT_URL') + f'/quizly/quiz/issue/{self.quiz.id}?question={self.question.id}'
                if self.quiz.is_ai_generated:
                    subject = 'Hey There! Its seems like there is something wrong with your quiz'
                    body = report_emails(path)
                
                    try:
                        send_email(
                        subject=subject,
                        body=body,
                        recipients=developers_email
                        )
                    except Exception as e:
                        raise ValueError(e)
                
                if self.quiz.host:
                    try:
                        send_email(
                        subject=subject,
                        body=body,
                        recipients=self.quiz.host.user.email
                        )
                    except Exception as e:
                        raise ValueError(e)
    
    def save(self, *arg, **kwarg):
        self.check_if_user_has_reported_already()
        self.notify_host_on_issue()
        super().save(*arg, **kwarg)


    def __str__(self):
      return self.issue[:50]

    