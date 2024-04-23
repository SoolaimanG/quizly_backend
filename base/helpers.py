import random
import string
from django.core.mail import EmailMessage
from quizly_backend import settings
from django.core.exceptions import ValidationError
from difflib import SequenceMatcher
from django.db.models import Q, Count
from math import ceil
from django.utils import timezone
from typing import Dict, Any, List
from string import ascii_letters
    

def string_mistakes(a, b):
    return SequenceMatcher(None, a, b).ratio()

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

def mark_question_by_type(user_answer: str | List[str], question: Any, quiz_tracker: Any):

    
    def add_xp():
        quiz_tracker.XP += question.question_point
        quiz_tracker.save()
        
    def reduce_xp():
        quiz_tracker.XP = max(quiz_tracker.XP - question.question_point, 0)
        quiz_tracker.save()
    
    # Evaluate the user's answer
    evaluation_result = evaluate_user_answer(question, user_answer,)

    # Apply XP based on the evaluation result
    if evaluation_result['is_correct']:
        add_xp()
    else:
        reduce_xp()

    # Update quiz tracker
    quiz_tracker.questions_answered_by_student.add(question)
    quiz_tracker.answers.append({'question': question.question_body, 'user_answer': user_answer, 'question_id': str(question.id)})
    quiz_tracker.save()  # Save the update or record
        
def mark_quiz(question_id:str, user_answer:str, quiz_tracker:Any | Any, auth: bool):
    from base.models import Question, Quiz
    quiz = quiz_tracker.quiz
    question = Question.objects.get(id=question_id)
    
    if quiz != question.quiz_id: #Making sure the id of the quiz pass is correct
        raise ValueError('Question passed not matching with quiz id')
    
    #Get the question types
    #question_type = question.question_type
    
    if auth:
        try:
    
            #This means mark on going to next question
            if quiz.result_display_type  == Quiz.ResultDisplayType.ON_COMPLETE or quiz.result_display_type == Quiz.ResultDisplayType.ON_SUBMIT:
                mark_question_by_type(user_answer=user_answer,question=question, quiz_tracker=quiz_tracker)

    
            #Do not mark save for the teacher to come and mark
            if quiz.result_display_type == Quiz.ResultDisplayType.MARK_BY_TEACHER:
                quiz_tracker.answers.append({'question': question.question_body,'user_answer': user_answer, 'question_id': str(question.id)})
                quiz_tracker.save()
        except Exception as e:
            raise ValueError(str(e))
    else:
        
        mark_question_anonymous(
            user_answer=user_answer,
            quiz_tracker=quiz_tracker,
            question=question
        )
        
def get_next_question(quiz_id: str, size: int, auth: bool):
    from base.models import Question
    # Get all the questions of a particular quiz that the user hasn't answered yet
    size = int(size) if auth else 5
    
    unanswered_questions = Question.objects.filter(quiz_id__id=quiz_id).values_list('id',flat=True)[:size]
    
    if not unanswered_questions:
        raise ValueError('No questions left for you to answer')

    return unanswered_questions

def get_trending_quiz(size: int):
    from base.models import Quiz
    trending_quiz = Quiz.objects.annotate(participants_count=Count('participants')).order_by('-participants_count')[:size]
    
    
    return trending_quiz

def mark_as_completed(quiz_tracker: Any):
    
    quiz_tracker.is_completed = True
    quiz_tracker.save()
        
    return quiz_tracker.is_completed

def mark_question_anonymous(user_answer: str | List[str], question: Any, quiz_tracker: Any):
    from base.models import AttemptedQuizByAnonymousUser
    anonymous_user = quiz_tracker.attempted_by

    # Evaluate the user's answer
    evaluation_result = evaluate_user_answer(question=question, user_answer=user_answer)


    # Save the quiz tracker with user answer
    _ , created = AttemptedQuizByAnonymousUser.objects.get_or_create(
        quiz=quiz_tracker.quiz,
        question=question,
        attempted_by=anonymous_user,
        defaults={
            'user_answer': user_answer,
            'xp_earn': question.question_point if evaluation_result['is_correct'] else 0,
        }
    )

    if not created and not quiz_tracker.user_answer:
        _.user_answer = user_answer
        _.xp_earn = question.question_point if evaluation_result['is_correct'] else 0
        # Save the quiz tracker after updating user_answer
        _.save()

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
        
def check_access_token(access_token: str, quiz: Any):
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

def evaluate_user_answer(question: Any, user_answer: str) -> Dict[str, Any]:
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

def check_quiz_type(quiz: Any, request: Any):
    
    user = request.user
    
    if quiz.allowed_users == quiz.ALLOWEDUSERS.AUTHENTICATED_USERS and not request.user.is_authenticated:
        raise ValueError('Quiz is only available for authenticated users')
    
    if quiz.allowed_users == quiz.ALLOWEDUSERS.ONLY_MY_STUDENTS:
        teacher = quiz.host
        #The host of the quiz is the teacher and the student is the student
        am_a_member = teacher.students.filter(user=user).exists()
        
        if not am_a_member:
            raise ValueError('Quiz is only available for students of this tutor')

def calculate_percentage_similarity(value1: int, value2: int) -> float:

    return min(value1, value2) / max(value1, value2) * 100

def give_user_feedback(user_xp: int, expected_xp: int) -> str:
    if user_xp is None or expected_xp is None:
        raise ValueError("Unable to determine feedback")

    similarity_percentage = calculate_percentage_similarity(user_xp, expected_xp)

    if similarity_percentage >= 90:
        return "Excellent! You've exceeded the expected score."
    elif similarity_percentage >= 70:
        return "Great job! You've scored above the average."
    elif similarity_percentage >= 50:
        return "Good effort! You're almost at the average score."
    else:
        return "Poor performance. Keep practicing to improve."
    
def create_result_response_data(score_board, total_question):
    # Construct data dictionary
    data = {
        'feedback': score_board.feedback,
        'xp_earn': score_board.xp_earn,
        'attempted_questions': score_board.attempted_question,
        'start_time': score_board.start_time,
        'end_time': score_board.end_time,
        'wrong_answers': score_board.wrong_answers,
        'corrections': score_board.corrections,
        'total_questions': total_question,
        'expected_xp': score_board.expected_xp
    }

    return data

def upload_to(instance, filename):
    return 'images/{filename}'.format(filename=filename)

def check_quiz_time(quiz: str, anonymous_id: str, user: Any):
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


