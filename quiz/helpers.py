
from .models import Quiz, QuizAccessToken, StudentAccount, QuizzesAttemptedByUser, AnonymousUser, Question, AttemptedQuizByAnonymousUser, UserAnswerForQuestion, MultipleChoiceOption
from typing import Any, List

from base.models import User

from django.utils import timezone
from django.shortcuts import get_object_or_404



# ---------Functions Starts Here
def check_access_token(token: str, quiz: Quiz, user: User):
    """
    The function `check_access_token` verifies the validity and expiration of an access token for a quiz
    and adds a user to the access token table if valid.
    
    :param token: The `token` parameter is a string representing the access token that a user needs to
    provide in order to access a specific quiz
    :type token: str
    :param quiz: Quiz object representing a quiz that users can access. It contains information about
    the quiz such as access settings and expiration time
    :type quiz: Quiz
    :param user: The `user` parameter in the `check_access_token` function represents the user who is
    trying to access a quiz. This user must have a valid access token in order to access the quiz
    :type user: User
    """
    
    if quiz.access_with_key and not token:
        raise ValueError('This Quiz can only be access with a token, please contact the host to get your token')
    
    access_token = QuizAccessToken.objects.filter(access_token=token, quiz=quiz).first()
    
    token_has_expire = access_token.expiration_time < timezone.now()
    
    if not access_token:
        raise ValueError('Invalid access token')
    
    if access_token.should_expire and access_token.expiration_time < token_has_expire:
        raise ValueError('Access token has expired')
    
    # Add user to the Access-Token Table
    access_token.add_user(user_id=user.id)

def get_trending_quiz(size: int | str):
    size = int(size)
    """
    The function `get_trending_quiz` retrieves a specified number of quizzes ordered by rating and
    number of participants.
    
    :param size: The `size` parameter in the `get_trending_quiz` function specifies the number of
    trending quizzes that you want to retrieve from the database. It determines how many quizzes will be
    included in the result set that is returned by the function
    :type size: int
    :return: A list of trending quizzes, sorted by rating and number of participants, with a specified
    size.
    """
    return Quiz.objects.order_by('-rating', '-participants')[:size]

def check_if_user_can_participate(quiz: Quiz, request: Any):
    """
    The function `check_quiz_type` verifies the access and user permissions for a quiz based on the
    provided request data.
    
    :param quiz: The `quiz` parameter in the `check_quiz_type` function is of type `Quiz`, which likely
    represents a quiz object with properties and methods related to a quiz
    :type quiz: Quiz
    :param request: The `request` parameter seems to be an object that contains user information and
    data related to a quiz. It likely comes from a request made to a web server or API. The `request`
    object seems to have attributes like `user` and `data`
    :type request: Any
    """
    
    user:User = request.user
    data = request.data
    
    if quiz.access_with_key: check_access_token(
        token=data['access_token'],
        quiz=quiz,
        user=user
    )
    
    if quiz.allowed_users == quiz.UsersToParticipate.AUTHENTICATED_USERS and not user.is_authenticated:
        raise ValueError('Quiz is only available for authenticated users')
    
    if quiz.allowed_users == quiz.UsersToParticipate.ONLY_MY_STUDENTS:
        #The host of the quiz is the teacher and the student is the student
        quiz.host.students.get(user=user)

def participate_as_authenticated_user(user: User, quiz: Quiz):
    
    try:
        student = get_object_or_404(StudentAccount, user=user)
    except StudentAccount.DoesNotExist:
        raise ValueError({'error':'student-account-does-not-exist'})
    
    quiz.participants.add(student)
    
    # Create a quiz tracker for the user
    tracker = QuizzesAttemptedByUser.objects.get_or_create(student=student, quiz=quiz, defaults={
        'student': student,
        'quiz': quiz,
        'is_completed': False
    })
    
    if tracker[0].is_completed:
        raise ValueError('User has already completed this quiz')
    
def participate_quiz_as_anonymous_user(anonymous_id: str, ip_address: str, quiz: Quiz):
    anonymous_user, _ = AnonymousUser.objects.get_or_create(anonymous_id=anonymous_id, defaults={
        'ip_address': ip_address,
        'anonymous_id':anonymous_id
    })
    
    tracker = AttemptedQuizByAnonymousUser.objects.get_or_create(quiz=quiz,anonymous_user=anonymous_user, defaults={
        'quiz': quiz,
        'anonymous_user': anonymous_user
    })
    
    if tracker[0].is_completed:
        raise ValueError({'error':'quiz-completed'})
    
def get_quiz_questions(quiz: Quiz, request: Any):
    user:User = request.user
    
    size = 10 if user.is_anonymous else None
    
    questions = Question.objects.filter(quiz=quiz).all().values_list('id', flat=True)[:size]

    return questions

def get_unanswered_questions(quiz: Quiz, request: Any):
    """
    The function `get_unanswered_questions` retrieves unanswered questions for a quiz based on the
    user's authentication status.
    
    :param quiz: The `quiz` parameter in the `get_unanswered_questions` function is an object
    representing a specific quiz. It is used to filter questions based on the quiz for which unanswered
    questions need to be retrieved
    :type quiz: Quiz
    :param request: The `request` parameter in the `get_unanswered_questions` function is typically an
    HTTP request object that contains information about the current request being made to the server. It
    can include details such as user authentication status, user session data, request method (GET,
    POST, etc.), and other metadata related
    :type request: Any
    :return: A list of unanswered questions for the given quiz based on the user's authentication
    status.
    """
    
    user:User = request.user
    questions = []
    
    if user.is_authenticated:
        questions_attempted = get_object_or_404(QuizzesAttemptedByUser, quiz=quiz, student__user=user).questions_attempted.all().values_list('id', flat=True)
        questions = Question.objects.filter(quiz=quiz).exclude(id__in=questions_attempted).values_list('id', flat=True)
        
    if user.is_anonymous:
            questions_attempted = AttemptedQuizByAnonymousUser.objects.filter(quiz=quiz).values_list('question__id', flat=True)
            questions = Question.objects.filter(quiz=quiz).exclude(id__in=questions_attempted).values_list('id', flat=True)
        
    return questions
        
def handle_user_participation(user: User, anonymous_id: str, ip_address: str, quiz: Quiz):
    """
    This function handles user participation in a quiz, either as an authenticated user or as an
    anonymous user.
    
    :param user: User object representing the user participating in the quiz
    :type user: User
    :param anonymous_id: The `anonymous_id` parameter is a unique identifier assigned to an anonymous
    user who is participating in the quiz. It helps track the anonymous user's progress and responses
    without revealing their identity
    :type anonymous_id: str
    :param ip_address: The `ip_address` parameter in the `handle_user_participation` function is a
    string that represents the IP address of the user who is participating in the quiz. The IP address
    is used to identify the user's device or network location. In this context, it is being passed as an
    argument to
    :type ip_address: str
    :param quiz: A quiz object that represents the quiz that the user wants to participate in
    :type quiz: Quiz
    """
    if user.is_authenticated:
        participate_as_authenticated_user(user=user)
        
    if user.is_anonymous:
        participate_quiz_as_anonymous_user(anonymous_id=anonymous_id, ip_address=ip_address[0], quiz=quiz) 

def handle_timer_check_for_authenticated_and_unauthenticated_users(quiz:Quiz, tracker: QuizzesAttemptedByUser | AttemptedQuizByAnonymousUser):
    """
    This function calculates the remaining time for a user to complete a quiz based on their
    authentication status and time spent.
    
    :param user: The `user` parameter represents the user accessing the quiz. It can be either an
    authenticated user (logged in) or an anonymous user (not logged in)
    :type user: User
    :param quiz: The function `handle_timer_check_for_authenticated_and_unauthenticated_users` takes two
    parameters: `user` of type `User` and `quiz` of type `Quiz`. The function checks whether the user is
    authenticated or anonymous, retrieves the start time of the quiz attempt, calculates the time the
    user has
    :type quiz: Quiz
    :return: The function `handle_timer_check_for_authenticated_and_unauthenticated_users` returns the
    remaining time in minutes for a user to complete a quiz.
    """
        
    time_user_has_spent = timezone.now() - tracker.start_time
    time_user_has_spent_in_seconds = time_user_has_spent.seconds / 60
    
    time_remaining = max(0, quiz.time_limit - time_user_has_spent_in_seconds)
    
    return time_remaining

def verify_user_participation(quiz: Quiz, request: Any):
    user:User = request.user
    
    if user.is_authenticated:
        tracker = get_object_or_404(QuizzesAttemptedByUser, quiz=quiz, student__user=user)
        
    if not quiz.is_published:
        raise ValueError('Something went wrong: This often happens if the quiz is not yet published')
    
    if user.is_anonymous:
        tracker = get_object_or_404(AttemptedQuizByAnonymousUser, quiz=quiz, anonymous_user__anonymous_id=request.data['anonymous_id'])
    
    return tracker
    
def handle_quiz_timer(quiz:Quiz, tracker: QuizzesAttemptedByUser | AttemptedQuizByAnonymousUser):
    """
    The function `handle_quiz_timer` checks the time remaining for a user to complete a quiz and raises
    an error if the time limit is surpassed.
    
    :param quiz: The `quiz` parameter is an object of type `Quiz`, which likely contains information
    about a quiz such as questions, options, and time limits
    :type quiz: Quiz
    :param request: The `request` parameter is typically an object that contains information about the
    incoming request to the server. It can include details such as the user making the request, any data
    being sent along with the request, headers, cookies, and more. In the context of the
    `handle_quiz_timer` function,
    :type request: Any
    :return: The function `handle_quiz_timer` is returning the remaining time for the user to complete
    the quiz.
    """
    
    if not bool(quiz.time_limit):
        return
    
    time_remaining = handle_timer_check_for_authenticated_and_unauthenticated_users(quiz, tracker)
    
    
    if not bool(time_remaining):
        raise ValueError("Something went wrong: You have surpass the time assign to complete this quiz, dont worry your response has been recorded.")
    
    return time_remaining

# MAIN FUNCTION THAT CONTROLS MARKING USER ANSWER
def save_user_response(quiz:Quiz, request: Any, question:Question, tracker: QuizzesAttemptedByUser | AttemptedQuizByAnonymousUser):
    user:User = request.user
    user_answer = request.data['user_answer']
    
    question_has_been_attempted = tracker.questions_attempted.get(question=question)
    
    # If user has already answer the question do not allow to re-do the question if the type is ON-COMPLETE
    if question_has_been_attempted and quiz.result_display_type == quiz.ResultDisplayType.ON_COMPLETE:
        raise ValueError('You already answer to this question, please move on to the next question if there is any.')
    
    handle_quiz_timer(quiz, tracker)
    
    result = assign_point_to_user(user_answer, tracker, question)

    user_response, created = UserAnswerForQuestion.objects.get_or_create(question=question, user=user, defaults={
        'question': question,
        'user': user.id or tracker.anonymous_user.anonymous_id,
        'answer': user_answer
    })
    
    if not created:
        user_response.answer = user_answer
        user_response.save()
        
    return result
    
def evaluate_user_response(question: Question, user_answer: str):
    
    result = {'is_correct': False, 'question_explanation': '', 'correct_answer':[]}
    
    if question.QuestionTypes.MULTIPLE_CHOICES == question.question_type and question.QuestionTypes.OBJECTIVE == question.question_type:
        result = evaluate_multiple_choice_question(question, user_answer)
          
    if question.QuestionTypes.TRUE_OR_FALSE == question.question_type:
        result = evaluate_true_or_false_question()
    
    if question.QuestionTypes.OPEN_ENDED == question.question_type:
        result = evaluate_open_end_question(question, user_answer)
    
    return result

def evaluate_multiple_choice_question(question: Question, user_answer: List[str]):
    
    result = {'is_correct': False, 'question_explanation': '', 'correct_answer':[]}
    
    correct_answers = MultipleChoiceOption.objects.filter(question=question, is_correct=True).values_list('body', flat=True)
    result['is_correct'] = all(answer in user_answer for answer in correct_answers)
    result['correct_answer'] = list(correct_answers)
    result['question_explanation'] = ', '.join(correct_answers)
    
    return result

def evaluate_open_end_question(question: Question, user_answer: List[str]):
    
    result = {'is_correct': False, 'question_explanation': '', 'correct_answer':[]}
    
    correct_answer = question.answer.lower().strip()
    user_answer = str(user_answer).lower().strip()
    mistakes_to_ignore = question.mistakes_to_ignore
    if mistakes_to_ignore is not None:
        mistakes_count = sum(1 for a, b in zip(correct_answer, user_answer) if a != b)
        result['is_correct'] = mistakes_count <= mistakes_to_ignore
    else:
        result['is_correct'] = correct_answer == user_answer
        
    result['question_explanation'] = question.correct_answer_explanation
    result['correct_answer'] = question.answer
        
    return result

def evaluate_true_or_false_question(question: Question, user_answer: List[str]):
    
    result = {'is_correct': False, 'question_explanation': '', 'correct_answer':[]}
    
    correct_answer = str(question.answer_is_true).lower()
    result['correct_answer'] = correct_answer
    result['is_correct'] = correct_answer == str(user_answer).lower()
    result['question_explanation'] = question.correct_answer_explanation
    
    return result

def assign_point_to_user(user_answer: List[str], tracker: QuizzesAttemptedByUser, question: Question):
    
    def add_xp():
        tracker.xp_earn += question.question_point
    
    def reduce_xp():
        tracker.xp_earn = 0 if tracker.xp_earn - question.incorrect_answer_penalty <= 0 else tracker.xp_earn - question.incorrect_answer_penalty
    
    result = evaluate_user_response(question, user_answer)
    
    add_xp() if result['is_correct'] else reduce_xp()

    # Add question to the one answered by the user
    tracker.questions_attempted.add(question)
    tracker.save()
    
    return result

def handle_quiz_submission(tracker: QuizzesAttemptedByUser | AttemptedQuizByAnonymousUser, user: User):
    user_id = user.id if user.is_anonymous else tracker.anonymous_user.anonymous_id
    user_answers = UserAnswerForQuestion.objects.filter(quiz=tracker.quiz, user_id=user_id).values_list('answer', flat=True)
    questions = Question.objects.filter(quiz=tracker.quiz).all()
    
    
    data = {'wrong_answers': 0, 'corrections': [], 'xp_earn': tracker.xp_earn, 'start_time': tracker.start_time, 'questions_attempted': user_answers.count(), 'feedback': give_user_feedback(tracker.xp_earn, 10), 'questions_answered': user_answers.count()}
    
    for question, user_answer in zip(questions, user_answers):
        result = evaluate_user_response(question, user_answer)
        
        if not result['is_correct']:
            data['wrong_answers'] += 1
            data['corrections'].append(question.question.correct_answer_explanation)
            
    return data

# GOOGLE GEMINI WROTE THIS
def calculate_percentage_similarity(value1: int, value2: int) -> float:
    """Calculates the percentage similarity between two values.

    Args:
        value1: The first value.
        value2: The second value.

    Returns:
        The percentage similarity between the two values (0 to 100).
    """
    
    # Avoid unnecessary multiplication by 100 if the values are the same
    if value1 == value2:
        return 100.0
    
    # Use absolute difference for efficiency
    absolute_difference = abs(value1 - value2)
    return min(value1, value2) / max(value1, value2) * 100 if absolute_difference > 0 else 0.0

# GOOGLE GEMINI WROTE THIS
def give_user_feedback(user_xp: int, expected_xp: int) -> str:
    """Provides feedback to the user based on their XP compared to expected XP.

    Args:
        user_xp: The user's earned XP.
        expected_xp: The expected XP for the activity.

    Returns:
        A feedback message based on the user's performance.

    Raises:
        ValueError: If either user_xp or expected_xp is None.
    """
    
    if user_xp is None or expected_xp is None:
        raise ValueError("Unable to determine feedback")

    feedback_map = {
        0.9: "Excellent! You've exceeded the expected score.",
        0.7: "Great job! You've scored above the average.",
        0.5: "Good effort! You're almost at the average score.",
        0.0: "Poor performance. Keep practicing to improve."
    }
    
    similarity_percentage = calculate_percentage_similarity(user_xp, expected_xp)
    return feedback_map.get(round(similarity_percentage / 10, 1), "Keep practicing to improve!")  # Default feedback

def mark_quiz_as_completed(tracker: QuizzesAttemptedByUser | AttemptedQuizByAnonymousUser):
    
    tracker.is_completed = True
    tracker.end_time = timezone.now()
    tracker.save()

def get_a_quick_quiz_for_user(user:User):
    student_favourite_subjects = StudentAccount.objects.filter(user=user).values_list('favourites', flat=True)[0] if user.is_authenticated else None
    
    if student_favourite_subjects:
        return Quiz.objects.filter(category=student_favourite_subjects, is_published=True).first()


    return get_trending_quiz(2).first()









