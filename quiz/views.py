from datetime import timedelta


from rest_framework.response import Response
from rest_framework.decorators import APIView, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from ipware import get_client_ip

from base.models import User, StudentAccount
from .models import Quiz, QuizComments, Question, QuizScoreBoard, AttemptedQuizByAnonymousUser, QuizzesAttemptedByUser

from serializers import UUIDListSerializer

from .serializers import QuizSerializer, QuizCommentSerializer, QuestionSerializer, QuizScoreBoardSerializer

from django.db import models
from django.shortcuts import get_object_or_404
from django.db.transaction import atomic
from django.core.cache import cache
from django.utils import timezone


from .helpers import check_if_user_can_participate, get_quiz_questions, get_unanswered_questions, handle_user_participation, handle_quiz_submission, verify_user_participation, save_user_response, mark_quiz_as_completed, get_a_quick_quiz_for_user, get_trending_quiz

@api_view(['GET'])
def recommended_quiz(request):
    try:
        data = request.query_params
        user:User = request.user
        size = data.get('pages', 5)
        
        default_category = ['Computer', 'Physics', 'Mathematics', 'English', '']
            
        if user.is_authenticated:
            student_favourite_subjects = StudentAccount.objects.filter(user__id=user.id).values_list('favourites__body', flat=True)
            categories = student_favourite_subjects or default_category
            quizzes = Quiz.objects.filter(category__body__in=categories, is_published=True).order_by('-rating', '-participants')[:size]
        
        if user.is_anonymous:
            # Annotate the queryset with the count of participants
            quizzes = get_trending_quiz(size)
            
        data = QuizSerializer(quizzes, context={'user': user, 'anonymous_id': data.get('anonymous_id', '')}, many=True)
        return Response({'data':data.data,'message':'OK'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'data':{},'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@atomic()
def start_quiz(request, quiz_id:str):
    try:
        data = request.data
        
        user: User = request.user
        anonymous_id = data.get('anonymous_id', '') #While this is optional it helps track users score when there are not authenticated
        ip_address = data.get('ip_address', get_client_ip(request)[0])
        
        
        try:
            quiz:Quiz = get_object_or_404(Quiz, id=quiz_id)
        except Quiz.DoesNotExist as e:
            return Response({'data':{},'message':str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        
        # This will check if the current user is eligible to participate in the quiz
        check_if_user_can_participate(quiz, request)
        
        # If user is eligible this will handle their participation like creating a tracker for user.
        handle_user_participation(user, anonymous_id, ip_address, quiz)
        
        questions = get_unanswered_questions(quiz=quiz, request=request) if data.get('unanswered-questions', False) else get_quiz_questions(quiz=quiz, request=request)
        data = UUIDListSerializer(data={'uuids': questions})
        
        if not data.is_valid():
            return Response({'data':{},'message':str(data.errors)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
     
        return Response({'data':data.data,'message':'OK'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'data': str(e),'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_quiz_questions_api(request, quiz_id:str):
    try:
        user:User = request.user
        data = request.data
        anonymous_id = data.get('anonymous_id', '')
        ip_address = data.get('ip_address', get_client_ip(request)[0])
        
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        
        handle_user_participation(user, anonymous_id, ip_address, quiz)
        
        questions = get_quiz_questions(quiz, request)
        data = UUIDListSerializer(data={'uuids': questions}, many=True)
        
        if not data.is_valid():
            return Response({'data':{},'message': str(data.errors)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'data':data.data,'message':'Ok'}, status= status.HTTP_200_OK)
    except Exception as e:
        return Response({'data':{},'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def mark_user_question_as_answered(request, question_id: str):
    try:
        
        question = get_object_or_404(Question, id=question_id)
        quiz = get_object_or_404(Quiz, id=question.quiz.id)
        
        check_if_user_can_participate(quiz, request)
        
        tracker = verify_user_participation(quiz, request)
        
        # This marks user answer if the quiz is on complete or on submit
        result = save_user_response(quiz, request, question, tracker)
        
        if quiz.result_display_type != quiz.ResultDisplayType.ON_COMPLETE:
            result['is_correct'] = None
            result['correct_answer'] = []
            result['question_explanation'] = None
        
        return Response({'data':{**result},'message':'OK'}, status=status.HTTP_200_OK)
        
    except Question.DoesNotExist as e:
        return Response({'data':{},'message':str(e)}, status=status.HTTP_404_NOT_FOUND) 
    except Exception as e:
        return Response({'data':{},'message':str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

@api_view(['GET'])
def get_quick_quiz_for_user(request):
    try:
        user: User = request.user
        
        two_minutes_ago = timezone.now() - timedelta(minutes=2)
        
        tracker = QuizzesAttemptedByUser.objects.filter(student__user=user, is_completed=True).order_by('end_time').first() if user.is_authenticated else None

        if tracker and tracker.end_time > two_minutes_ago:
            return Response({'data':{'error': 'quick-quiz-cool-off'}, 'message':'Please take a brief pause. We will be ready for you again shortly.'}, status=status.HTTP_425_TOO_EARLY)
        
        if tracker and not tracker.is_completed:
            data = QuizSerializer(tracker.quiz)
            return Response({'data':data.data,'message':''}, status=status.HTTP_200_OK)
        
        quiz = get_a_quick_quiz_for_user(user)
        
        data = QuizSerializer(quiz)
        
        return Response({'data':data.data,'message':'OK'}, status=status.HTTP_200_OK)
        
        # First get a quiz that user has not attempted
    except Exception as e:
        print(e)
        return Response({'data':{},'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuestionAPI(APIView):
    def get(self, request, question_id:str):
        try:
            
            question = get_object_or_404(Question, id=question_id)
            
            quiz:Quiz = get_object_or_404(Quiz, id=question.quiz.id)
            
            # Include access token if its required
            check_if_user_can_participate(quiz, request)
            
            verify_user_participation(quiz, request)
            
            data = QuestionSerializer(question)
            
            return Response({'data':data.data, 'message':''}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'data': str(e),'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExplorePageQuizAPI(APIView):
    # Get quizzes
    def get(self, request):
        pass
            
            
            # @api_view(['GET'])

# @permission_classes([IsAuthenticated])
class QuizCommentsAPI(APIView):
    def get(self,request, quiz_id: str):
        try:
            user:User = request.user
            quiz = get_object_or_404(Quiz, id=quiz_id)
            comments = QuizComments.objects.filter(quiz=quiz).order_by('-created_at')
        
        
            if user.is_authenticated:
                pages = request.query_params.get('pages', 20)
                pages = int(pages)
            
                comments = comments[:pages]
            else:
                comments = comments[:10]
            
            data = QuizCommentSerializer(comments, many=True)
        
            return Response({'data':data.data,'message':'OK'},status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'data':{},'message':str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, quiz_id: str):
        pass

class QuizAPI(APIView):
    def get(self, request, quiz_id: str):
        try:
            user: User = request.user
            quiz = cache.get(f'quiz_{quiz_id}')
            
            if quiz:
                data = QuizSerializer(quiz)
                return Response({'data':data.data, 'message':'OK'}, status=status.HTTP_200_OK)
            
            quiz = get_object_or_404(Quiz, id=quiz_id)
            data = QuizSerializer(quiz, context={'user': user, 'anonymous_id': request.query_params.get('anonymous_id', '')})
            
            # Setting the cache
            cache.delete(f"quiz_{quiz_id}")
            cache.set(f'quiz_{quiz_id}', data)
            
            return Response({'data':data.data, 'message':'OK'}, status=status.HTTP_200_OK)
            
        except Quiz.DoesNotExist as e:
            return Response({'data':{},'message': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class QuizResult(APIView):
    def get(self, request, quiz_id: str):
        try:
            user: User = request.user
            data = request.query_params
            # ip_address = data.get('ip_address', get_client_ip(request)[0])
            
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            tracker = verify_user_participation(quiz, request)
            
            if not tracker.is_completed:
                return Response({'data':{'error':'quiz-is-not-submitted'},'message': 'Something went wrong: You participated in this quiz but it looks like you have not submitted this quiz'}, status=status.HTTP_)
            
            
            if user.is_authenticated:
                quiz_result = get_object_or_404(QuizScoreBoard, user__user=user, quiz=quiz)
                
                data = QuizScoreBoardSerializer(quiz_result)
                return Response({'data': data.data,'message': "OK"}, status=status.HTTP_200_OK)
            
            if user.is_anonymous:
                tracker = get_object_or_404(AttemptedQuizByAnonymousUser, anonymous_user__anonymous_id=data['anonymous_id'], quiz=quiz)
                data = handle_quiz_submission(tracker, user)
                
                return Response({'data':data,'message': 'OK'}, status=status.HTTP_200_OK)
            
        except Quiz.DoesNotExist as e:
            return Response({'data':{},'message': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, quiz_id: str):
        try:
            data = request.data 
            user:User = request.user
            
            ip_address = data.get('ip_address', get_client_ip(request)[0])
            
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            handle_user_participation(user, data['anonymous_id'], ip_address )
            
            tracker =  verify_user_participation(quiz, request)
            
            # Get all the questions user answer
            data = handle_quiz_submission(tracker, user)
            
            
            score_board = QuizScoreBoard(
                user=tracker.student,
                quiz=tracker.quiz,
                corrections=data['corrections'],
                feedback=data['feedback'],
                questions_answered=data['questions_answered'],
                xp_earn=tracker.xp_earn,
                expected_xp='',
                start_time=tracker.start_time,
                end_time=tracker.end_time
            )
            
            if user.is_authenticated: score_board.save()
            
            mark_quiz_as_completed(tracker)
            
            return Response({'data':{},'message':'OK'}, status=status.HTTP_200_OK)
            
        except Quiz.DoesNotExist as e:
             return Response({'data':{},'message': str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




