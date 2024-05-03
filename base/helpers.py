import random
import string
from django.core.mail import EmailMessage
from quizly_backend import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from math import ceil
from django.utils import timezone
from typing import Any, List
from string import ascii_letters
    
def send_email(subject: str, body: str, recipients: List[str]):
    try:
        email = EmailMessage(
            subject,
            body,
            from_email=settings.EMAIL_HOST_USER,
            to=recipients
        )
        email.send()
    except ValidationError as e:
        # ValidationError is raised for invalid email addresses
        raise ValidationError(f"Invalid recipient email address: {e}")
    except Exception as e:
        # Catch other exceptions and log or handle them appropriately
        raise Exception(f"Error sending email: {e}")

def generate_otp(len:int) -> str:
    
    otp = ''
    for i in range(len):
        random_num = random.randint(0, 9)
        otp += str(random_num)
    return otp

def generate_random_email() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20)) + '@gmail.com'

def generate_random_password(len: int):
    return "".join(random.choices(string.ascii_letters + string.ascii_uppercase + string.ascii_uppercase, k=len))
        
def has_started_quiz(auth: bool, anonymous_user: Any, user: Any, quiz: Any):
    from base.models import AttemptedQuizByAnonymousUser, StudentAccount, AttemptedQuizOfUser
    
    if auth:
        student = StudentAccount.objects.filter(user=user).first()
        
        if not student:
            return False
        
        return AttemptedQuizOfUser.objects.filter(
            Q(quiz=quiz) & Q(attempted_by=student)
            ).exists()
    else:
        if anonymous_user is None:
            return False
        
        return AttemptedQuizByAnonymousUser.objects.filter(
            Q(quiz=quiz) & Q(attempted_by=anonymous_user)
            ).exists()
        
# def check_access_token(access_token: str, quiz: Any):
    from base.models import QuizAccessToken
    if not all([access_token, quiz]):
        raise ValueError('Invalid access token')
    
    allow_user = QuizAccessToken.objects.filter(
        Q(access_token=access_token) & Q(quiz=quiz)
    ).first()
    
    current_time = timezone.now()
    
    if not allow_user:
        raise ValueError('Invalid access token')
    
    if allow_user.should_expire and allow_user.expiration_time < current_time:
        raise ValueError('Access token has expired')
    
    if allow_user.usage >= allow_user.number_of_usage:
        raise ValueError('Access token max usage reached')
    
    allow_user.usage += 1
    allow_user.save()
    
    return True

# def evaluate_user_answer(question: Any, user_answer: str) -> Dict[str, Any]:
    from base.models import ObjectiveOptions
    correct_options = ObjectiveOptions.objects.filter(
        belongs_to=question,
        is_correct_answer=True
    ).values_list('body', flat=True)
    
    question_type = question.question_type
    result = {'is_correct': False, 'explanation': '','correct_answer':''}

    if question_type == question.QuestionTypes.OBJECTIVE:
        result['correct_answer'] = correct_options[0]
        result['is_correct'] = correct_options[0] == user_answer

    elif question_type == question.QuestionTypes.TRUE_OR_FALSE:
        result['correct_answer'] = str(question.answer_is_true).lower()
        result['is_correct'] = str(question.answer_is_true).lower() == str(user_answer).lower()


    elif question_type == question.QuestionTypes.GERMAN:
        if bool(question.mistakes_to_ignore) and ceil(string_mistakes(user_answer, question.answer)) > question.mistakes_to_ignore:
            result['is_correct'] = False
        elif question.is_strict:
            result['is_correct'] = question.answer.lower().strip() == str(user_answer).lower().strip()
        else:
            result['is_correct'] = True
    

    elif question_type == question.QuestionTypes.MULTIPLE_CHOICES:
        result['is_correct'] = all(choice in user_answer for choice in correct_options)


    result['explanation'] = question.correct_answer_explanation
    return result


def upload_to(instance, filename):
    return 'images/{filename}'.format(filename=filename)

# def check_quiz_time(quiz: str, anonymous_id: str, user: Any):
    from .models import User, Quiz, AttemptedQuizOfUser, AttemptedQuizByAnonymousUser
    user: User
    quiz: Quiz

    quiz_duration = quiz.time_limit#The duration like time set by the tutor to finish quiz
    current_time = timezone.now() #Current time 
    

    if user.is_authenticated:
            # Find the quiz tracker for authenticated user
        quiz_tracker = AttemptedQuizOfUser.objects.filter(quiz=quiz, attempted_by__user=user).first()

        if not quiz_tracker:
            raise ValueError("Unable to locate user quiz tracker.")

        start_time = quiz_tracker.start_time #This is the start-time of the quiz by user
    else:
        # Find quiz tracker for unauthenticated users
        quiz_tracker = AttemptedQuizByAnonymousUser.objects.filter(quiz=quiz, attempted_by__anonymous_id=anonymous_id).order_by('created_at').first()

        # Find the time the anonymous user start quiz
        start_time = quiz_tracker.created_at

     # Subtract the start-time from the current-time and check how many minute left
    time_spent = current_time - start_time

    # Get the remaining time in seconds and convert to minutes (Time set by the tutor will always be in minutes)
    time_spent = time_spent.seconds / 60

    remaining_time = max(0, quiz_duration - time_spent)
    # After finding the tracker check the time user start quiz and check if the time has elapses force submit the quiz
        
    # Check if the time user spent is greater than or equal to the assign
    """"
    If the user time has elapses send 0 seconds to the client and submit quiz on the server
    data return should be {
    time_remaining: int,
    }
    """
    if not bool(remaining_time):
            raise ValueError('Unauthorize perphaps your time is up with this quiz.')
    
    return remaining_time

def notification_helper(user, message: str, type:str, path: str, user_requesting):
    from .models import Notifications
    # user = user
    # user_requesting: User = user_requesting

    if type not in [Notifications.NotificationType.ACHIEVEMENT, Notifications.NotificationType.COMMUNITY_REQUEST, Notifications.NotificationType.DEFAULT, Notifications.NotificationType.NEW_QUIZ_ALERT]:
        raise ValueError('Notification type does not exist')

    notification = Notifications(
        user=user,
        message=message or '',
        path=path or None,
        notification_type=type,
        user_requesting=user_requesting or None
    )


    notification.save()
    
def generate_random_letters(length: int):
    letters = ascii_letters
    randoms = random.choices(letters, k=length)
    generated_string = ''.join(randoms)
    
    return generated_string


