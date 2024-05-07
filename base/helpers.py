import random
import string
from django.core.mail import EmailMessage
from quizly_backend import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import List
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


