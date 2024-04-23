from datetime import timedelta
from typing import List

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import requests

from .models import User, ForgetPassword, EmailVerification, StudentAccount, TeachersAccount,Category,Question,Quiz, Comments, AttemptedQuizOfUser, AnonymousUser, AttemptedQuizByAnonymousUser, ScoreBoard, SavedQuiz, Ratings, QuizReports, Notifications, FeatureWaitList
from rest_framework.response import Response
from rest_framework.decorators import permission_classes,api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR,HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS,HTTP_409_CONFLICT, HTTP_401_UNAUTHORIZED
from .helpers import generate_otp,send_email, generate_random_email,generate_random_password, mark_quiz, get_next_question, get_trending_quiz, has_started_quiz, check_access_token, evaluate_user_answer, check_quiz_type, give_user_feedback, create_result_response_data, mark_as_completed, notification_helper
from emails import otp_message, verify_email_address
from serializers import UserSerializer,CategorySerializer, QuizSerializer, QuestionSerializer, CommentsSerializer, UUIDListSerializer, ResultSerializer, RelatedQuizSerializer, RelatedQuizSerializerForTutor, NotificationSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from ipware import get_client_ip
from django.db import transaction


@api_view(['POST'])
def login_or_signup(request):
    
    try:
        user_data = request.data
    
        username = user_data.get('username') #Required parameter
        auth_provider = user_data.get('auth_provider') #Required parameter
        
        username = username.strip().lower() #Change username to lowercase and remove whitespace
        
        #If the user is logging in with Oauth this should extend the data to be received for the client
        
        #--->this parameters below are optional<---
        password = user_data.get('password','')
        email = user_data.get('email','')
        profile_image = user_data.get('profile_image','')
        email_verified = user_data.get('email_verified','')
        create_new_account = user_data.get('create_new_account','')
        email = email.strip()
        
        #Username is required for authentication so if it not provided the we can return an error
        if not username:
            return Response({'data':{},'message':"Missing required fields username"})
        
        #Password is neccesary but in the case where the user whats to login the app using oauth the password will not be provided so not happens execept for Local auth password is required.
        
        generated_password = generate_random_password(35)
        
        user = User.objects.filter(username=username).exists() #Loockup the user in the database and if it exists confirm credentials
        
        if not user and not bool(create_new_account):
            return Response({'data':{},'message':"User does not exist in the database"},status=HTTP_404_NOT_FOUND)
        
        __, created = User.objects.get_or_create(
            username=username,
            defaults={
                'auth_provider': auth_provider,
                'password': make_password(password) if auth_provider == 'L' else make_password(generated_password),
                'first_time_login': True,
                'email_verified': bool(email_verified),
                'account_type':'S',
                'signup_complete': False,
                'email': email or generate_random_email(),
                'profile_image': profile_image,
                'age': 10,
                'bio':''
            }
        )
        
        if not created:
            if __.auth_provider == 'L' and not __.check_password(password):
                return Response({'data':{},'message':"Incorrect password"},status=HTTP_409_CONFLICT)
            
            if __.auth_provider != 'L' and password and not __.check_password(password):
                return Response({'data':{},'message':"Incorrect password"},status=HTTP_409_CONFLICT)
                
            
            __.first_time_login = False 
            
        __.last_login = timezone.now()
        
        token = RefreshToken.for_user(__)
        token.set_exp(lifetime=timedelta(hours=5))
        
        #Notify the user about the new password created for them in case the want to login using L i.e Local Authentication
        data = UserSerializer(__)
        __data = {
        'password': generated_password if created and __.auth_provider != 'L' else '',
        'access_token': str(token.access_token),
        }
        
        __.save() #Save the user as first-timeer if the created is true and then false it means that the user is already in the database
        
        
        return Response({'data':{**__data, **data.data},'message':f"{__.username.capitalize()} logged in successfully"},status=HTTP_200_OK)
    
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
   
class ForgetPasswordApiView(APIView):
  def get(self, request):
     try:
        otp = request.query_params.get('otp')
        otp = otp.strip()
        
        if not otp:
           return Response({'data':{},'message':'Missing required parameter OTP'},status=HTTP_404_NOT_FOUND)
        
        try:
          forget_password = get_object_or_404(ForgetPassword, otp=otp)
        except ForgetPassword.DoesNotExist:
           return Response({'data':{},'message':'OTP is either do not exist or has been used'},status=HTTP_400_BAD_REQUEST)
        
        if forget_password.expires_by < timezone.now():
           return Response({'data':{},'message':'This OTP has expired. Please request a new one'},status=HTTP_400_BAD_REQUEST)
        
        return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
        
     except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
  
  def post(self, request):
        try:
            email = request.data.get('email')
            email = email.lower().strip()

            user = get_object_or_404(User, email=email)
            otp = generate_otp(5)

            expires_by = timezone.now() + timedelta(minutes=25)
            next_request = timezone.now() + timedelta(seconds=30)

            forget_password, created = ForgetPassword.objects.get_or_create(
                requested_by=user,
                defaults={
                    'expires_by': expires_by,
                    'number_of_request': 1,
                    'otp': otp,
                    'next_request': next_request
                }
            )

            if not created:
                if forget_password.next_request < timezone.now():
                    return Response(
                        {'data': {}, 'message': f'Please try again in {forget_password.next_request}'},
                        status=HTTP_429_TOO_MANY_REQUESTS
                    )

                forget_password.next_request = timezone.now() + timedelta(seconds=30 * forget_password.number_of_request)
                forget_password.expires_by = expires_by
                forget_password.number_of_request += 1
                forget_password.otp = otp

            try:
                message = otp_message(otp)

                send_email(
                    subject='Reset Password OTP',
                    body=message,
                    recipients=[email]
                )
            except Exception as e:
                return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

            forget_password.save()
            return Response({'data': {'time_uptil': forget_password.next_request}, 'message': 'An OTP has been successfully sent to the email provided'},
                            status=HTTP_200_OK)

        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
   
   #This is to verify the OTP and reset the user password
  
  def patch(self, request):
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')
            password = request.data.get('password')

            email = email.lower().strip()
            user = get_object_or_404(User, email=email)
            forget_password = get_object_or_404(ForgetPassword, requested_by__email=email, otp=otp)
            
            if timezone.now() > forget_password.expires_by:
               return Response({'data':{},'message':'This OTP has expired please request a new one'},status=HTTP_400_BAD_REQUEST)

            try:
                password_validation.validate_password(password)
            except Exception as e:
                return Response(
                    {'data': {}, 'message': f'Password must meet the following requirements: {", ".join(e)}'},
                    status=HTTP_400_BAD_REQUEST
                )

            user.set_password(password)
            user.save()

            forget_password.delete()

            return Response({'data': {}, 'message': 'Password reset successfully'}, status=HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'data': {}, 'message': 'User not found'}, status=HTTP_404_NOT_FOUND)

        except ForgetPassword.DoesNotExist:
            return Response({'data': {}, 'message': 'Invalid OTP or user email'}, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

#Routes that require authentication
@permission_classes([IsAuthenticated])
class UserApiView(APIView):
   @method_decorator(cache_page(60 * 30)) #Caching get user for 30minutes
   def get(self, request):
    
    try:
        param = request.query_params.get('params','')
        user:User = request.user #Get the current user thats looged in
        
        if param:
            
            user:User = User.objects.filter(
                Q(user_id=param) | Q(username=param) | Q(email=param)
            ).first()
            
            if not user:
                return Response({'data':{},'message':'User does not exist'},status=HTTP_404_NOT_FOUND)
            else:
                
                user_serializer = UserSerializer(user)
                serialized_data = user_serializer.data
                
                return Response({'data':serialized_data,'message':serialized_data},status=HTTP_200_OK)
            
        else:
            user_serializer = UserSerializer(user) #Serialize the user data i.e turn it to JSON readable
            serialized_data = user_serializer.data
            
            response = Response({'data':serialized_data,'message':'OK'},status=HTTP_200_OK)
            response['Access-Control-Allow-Credentials'] = 'true'
            
            return response
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
    
   
   def patch(self, request):
      try:
            user:User = request.user #Get the current user
          
            user_data = request.data
            
            # All the request data are optional
            email = user_data.get('email','')
            first_name = user_data.get('first_name','')
            last_name = user_data.get('last_name','')
            favourites = user_data.get('favourites','')
            age = user_data.get('age','')
            bio = user_data.get('bio','')
            profile_image = user_data.get('profile_image','')
            account_type = user_data.get('account_type','')
            
            #Teachers Data -->When editting the teacher profile if the user is a teacher
            educational_level = user_data.get('educational_level','')
            phone_num = user_data.get('phone_num','')
            whatsapp_link = user_data.get('whatsapp_link','')
            address = user_data.get('address','')
            
            #If we pass in the data we update them other wise leave them as they are before
            user.email = email or user.email
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.age = age or user.age
            user.bio = bio or user.bio
            user.profile_image = profile_image or user.profile_image
            user.account_type = account_type or user.account_type
            
            #Changing the state of the email verification in the case where email change
            user.email_verified = user.email_verified if user.email_verified and user.email == email else False
            
            if bool(favourites) and 2 >= len(favourites) >= 5:
             return Response({'data': {}, 'message': 'Select between two and five subjects'},status=HTTP_409_CONFLICT)
         
            if favourites:
                #Now that we are here, we will check if the user is a teacher we will use specialization and if its a student we will use favourite
                
                categories = [] #Initializing an empty list to store the user favourites
                
                for i in favourites:
                    try:
                       category = Category.objects.get(body=i)
                       categories.append(category)
                    except ObjectDoesNotExist:
                       return Response({'data': {}, 'message': "Category not found"},status=HTTP_404_NOT_FOUND)
                
                
                if user.account_type == 'T':
                    #--->Adding the user data recieve from the teacher
                    teacher, created = TeachersAccount.objects.get_or_create(
                        user=user,
                        defaults={
                        'educational_level':educational_level,
                        'phone_num':phone_num,
                        'whatsapp_link':whatsapp_link,
                        'address':address,
                        }
                    )
                    
                    
                    teacher.specializations.set(categories)
                    
                    #teacher.specializations.add(*categories)
                    if not created:
                        teacher.save()
                        
                        
                else:
                    student, created = StudentAccount.objects.get_or_create(
                        user=user,
                        defaults={
                            "streaks_count": 1
                        }
                    )
                
                    
                    student.favourites.set(categories)
                
                    if not created:
                        student.save()
                        
                
            #If the user has set his firstname, lastname and email and also email is verified then mark the user as completed sign up
            if all([user.first_name, user.last_name, user.email, user.email_verified]):
                user.signup_complete = True
            
            
            user.save() # as the name implies this is to save the editted model to the database
            
            if bool(email) and user.email == email:
      
               response = requests.post(os.environ.get('QUIZLY_API_URL')+'/api/v1/auth/verify-email/',data={'email':email})
               
               if not response.ok:
                   return Response({'data':{},'message': "Something went wrong..."},status=HTTP_500_INTERNAL_SERVER_ERROR)
           
            return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
      except Exception as e:
          return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyEmailApiView(APIView):
    
   def get(self, request):
      try:
         
         verify_token = request.query_params['verify_token']
         verify_token = str(verify_token).strip()
         
         email_verify = get_object_or_404(EmailVerification, verify_token=verify_token)
         
         already_verified = email_verify.user.email_verified
         
         if already_verified:
            return Response({'data':{},'message':'This email is already verified. Thank you'},status=HTTP_409_CONFLICT)
         
         if email_verify.expires < timezone.now():
            return Response({'data':{},'message':'Verify token expired. Please request new token'},status=HTTP_400_BAD_REQUEST)
         
         user = User.objects.get(email=email_verify.user.email)
         user.email_verified = True
         
         user.save()
         email_verify.delete()
         
         return Response({'data':{},'message': f'Your email has been successfully verified. Thank you {str(email_verify.user.username.capitalize())}'}, status=HTTP_200_OK)
         
      except Exception as e:
         return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
      
   def post(self, request):
    try:
        
        email = request.data.email
        email = email.strip()

        user = get_object_or_404(User, email=email)
        verify_token = uuid.uuid4()

        expiration_time = timezone.now() + timedelta(minutes=25)
        next_request = timezone.now() + timedelta(minutes=10)
        
        if user.email_verified:
           return Response({'data':{},'message':"Your email has already been verified"},status=HTTP_400_BAD_REQUEST)

        # Try to get or create an EmailVerification object for the user
        email_verify, created = EmailVerification.objects.get_or_create(
            user=user,
            defaults={
                'expires': expiration_time,
                'verify_token': verify_token,
                'number_of_requests': 1,
                'next_request': next_request
            }
        )

        if not created:
            # Update the existing EmailVerification object
            if email_verify.next_request > timezone.now():
                return Response(
                    {'data': {}, 'message': f"Please try again in {email_verify.next_request}"},
                    status=HTTP_429_TOO_MANY_REQUESTS
                )

            #email_verify.
            email_verify.expires = expiration_time
            email_verify.verify_token = verify_token
            email_verify.number_of_requests += 1
            email_verify.next_request = next_request

            # Keep next_request unchanged for an existing object

        try:
            verify_email_link = f'{os.environ.get("QUIZLY_CLIENT_URL")}/auth/confirm-email/{verify_token}'

            send_email(
                subject='Verify your email address',
                body=verify_email_address(verify_email_link),
                recipients=[email]
            )
       
        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
        
        email_verify.save()
        return Response({'data': {}, 'message': "Email verification link sent to your email address"},
                        status=HTTP_200_OK)

    except Exception as e:
        return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

#---->CATEGORY LOOKUPS<----
@api_view(['GET'])
def get_categories(request):
    
    try:
        categories = Category.objects.all()
        
        serializer = CategorySerializer(categories, many=True)
        serialized_data = serializer.data
        
        return Response({'data':serialized_data,'message':"OK"},status=HTTP_200_OK)
    except Exception as e:
        return Response({'data':{},'messages':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

#User APIs starts here
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_category(request):
  
    try:
        
        user:User = request.user
      
        if user.account_type == 'T':
          
          specialization = TeachersAccount.objects.get(user=user).specializations
          
          serializer = CategorySerializer(specialization,many=True)
          serialized_data = serializer.data
          
        else:
          
          favourites = StudentAccount.objects.get(user=user).favourites
          
          serializer = CategorySerializer(favourites,many=True)
          serialized_data = serializer.data
          
        return Response({'data':serialized_data,'message':'OK'},status=HTTP_200_OK)
      
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_quizzes(request):
    try:
        size = request.query_params.get('len','5')
        size = int(size)
        
        #If the user is authenticated find quizzes for user base on the user category
        if request.user.is_authenticated:
            pass
        else:
            quizzes = Quiz.objects.annotate(participants_count=models.Count('participants')).order_by('-participants_count')[:size] #This simply means get the quizzes most users attend
            data = QuizSerializer(quizzes, many=True)
        
        return Response({'data':data.data,'message':"OK"},status=HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_trending(request): 
    try:
        anonymous_id = request.query_params.get('anonymous_id')
        ip_address = request.query_params.get('ip_address', '123.54.98')
         
        trending_quiz = get_trending_quiz(1)
        has_user_started_quiz = False

        user:User = request.user
        # print(trending_quiz)
        
        if user.is_authenticated:
            user:User = request.user  # Current authenticated user
            has_user_started_quiz = has_started_quiz(
                auth=True,
                user=user,
                quiz=trending_quiz,
                anonymous_user='' #Anonymous user will be empty in this case cause user is authrnticated.
            )
        else:
            if anonymous_id:
                anonymous_user = AnonymousUser.objects.filter(
                    Q(anonymous_id=anonymous_id) | Q(ip_address=ip_address)
                ).first()
                if anonymous_user:
                    has_user_started_quiz = has_started_quiz(
                        auth=False,
                        anonymous_user=anonymous_user,
                        quiz=trending_quiz,
                        user=''
                    )

        # Provide context during serializer initialization
        serializer = QuizSerializer(trending_quiz, context={'has_user_started_quiz': has_user_started_quiz}, many=True)
        # Access the serialized data
        serialized_data = serializer.data

        return Response({'data': serialized_data, 'message': 'OK'}, status=HTTP_200_OK)
    except Exception as e:
        return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def quiz_comments(request, id):
    try:
        
        if not id:
            return Response({'data':{},'message':'Quiz Id is required.'},status=HTTP_404_NOT_FOUND)
        
        quiz = get_object_or_404(Quiz, id=id)
        comments = Comments.objects.filter(quiz=quiz).order_by('-created_at')
        
        
        if request.user.is_authenticated:
            size = request.query_params.get('size', 20)
            size = int(size)
            
            comments = comments[:size]
        else:
            comments = comments[:10]
            
        data = CommentsSerializer(comments, many=True)
        
        return Response({'data':data.data,'message':'OK'},status=HTTP_200_OK)
        
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def isUserAuthenticated(request):
    try:
        user:User = request.user
        return Response({'data':{},'message':"OK"},status=HTTP_200_OK)
        
    except Exception as e:
        print(e)
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@transaction.atomic
def start_quiz(request):
    try:
     data = request.data
     
     quiz_id = data.get('quiz_id')
     access_key = data.get('access_key','')
     anonymous_id = data.get('anonymous_id', '') #While this is optional it helps track users score
     ip_address = '123.129.00' or data.get('ip_address','')
     
     access_key = access_key.strip()
     
    
     quiz:Quiz = get_object_or_404(Quiz, id=quiz_id)# Get the current quiz to be attempted
     quiz_questions = Question.objects.filter(quiz_id=quiz).count() # List of number the questions related to the quiz
     
    # This checks if the request matches the quiz to be taken
     check_quiz_type(
         quiz=quiz,
         request=request,
     )
     
    #  The quiz needs access key to start
     if quiz.access_with_key:
         if not access_key:
            return Response({'data':{},'message':'This quiz requires access code to start'}, status=HTTP_404_NOT_FOUND)
        
        #Find key access code in DB
         try:
            check_access_token(access_token=access_key,quiz=quiz)
         except Exception as e:
            return Response({'data':{},'message':str(e)},status=HTTP_400_BAD_REQUEST)
     
     if request.user.is_authenticated:
         
      user:User = request.user #Current login user
     

      student = StudentAccount.objects.filter(user=user).first()

      if not student:
        return Response({'data':{},'message':"User is does not has a student account"},status=HTTP_409_CONFLICT)

        #  #If the user is not a participant of that quiz, then add the user as a  participant and start quiz
      if not quiz.participants.filter(id=student.id).exists():
        quiz.participants.add(student)
    
        #If user does not have a quiz tracker of that quiz already, Create one for them 
      quiz_tracker, ___ = AttemptedQuizOfUser.objects.get_or_create(quiz=quiz, attempted_by=student,
      defaults={
       'quiz':quiz,
       'is_completed':False,
       'attempted_by': student,
      })
    #  
      if quiz_tracker.is_completed:
       return Response({'data':{},'message':'You already completed this quiz'},status=HTTP_400_BAD_REQUEST)
   
      if quiz_tracker.quiz.allowed_users == quiz_tracker.quiz.ALLOWEDUSERS.ONLY_MY_STUDENTS:
        #  Check if user is a student of the tutor
        am_a_member = quiz_tracker.quiz.host.students.filter(id=student.id).exists()
        
        if not am_a_member:
            return Response({'data':{},'message': f'You are not a student of this tutor, subscribe to {quiz_tracker.quiz.host.user.username} to get access'},status=HTTP_401_UNAUTHORIZED)
      
     else:
         
        # This is use to create or get user if existing
        anonymous_user, created = AnonymousUser.objects.get_or_create(anonymous_id=anonymous_id,defaults={
            'ip_address': ip_address[0],
            'anonymous_id':anonymous_id
        })
        
        if not created and anonymous_user.completed_quiz.filter(id=quiz.id).exists():
            return Response({'data':{},'message':'You already completed this quiz. Go to settings and navigate to retake quiz'},status=HTTP_400_BAD_REQUEST)
        
        
        if quiz.allowed_users != quiz.ALLOWEDUSERS.ALL:
            return Response({'data':{},'message':'You are not allowed to participate in this quiz'},status=HTTP_401_UNAUTHORIZED)
        
        question = Question.objects.filter(quiz_id=quiz).first()
        AttemptedQuizByAnonymousUser.objects.get_or_create(
            quiz=quiz,
            attempted_by=anonymous_user,
            question=question
        )
     
     next_question = get_next_question(quiz.id, quiz_questions, request.user.is_authenticated)


     data = UUIDListSerializer(data={'uuids':next_question})
     
     if not data.is_valid():
         return Response({'data':{},'message':str(data.errors)},status=HTTP_500_INTERNAL_SERVER_ERROR)
     
     return Response({'data':data.data,'message':'OK'}, status=HTTP_200_OK)
     
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_student_or_teacher_account(request):
   try:
       data = request.data
       user:User = request.user
        
       account_type = data.get('account_type')
        
        #Data for student account
       difficulty = data.get('difficulty', '')
        
        #Data for teacher account
       phone_num = data.get('phone_num', '')
       whatsapp_link = data.get('whatsapp_link', '')
       address = data.get('address', '')
       educational_level = data.get('educational_level', '')
        
       account_exists = StudentAccount.objects.filter(user=user).exists() or TeachersAccount.objects.filter(user=user).exists()
        
       message = 'User already has a student account cannot create duplicate' if account_type == 'S' else 'User already has a teacher account cannot create duplicate'
        
       if account_exists:
         return Response({'data':{},'message':message},status=HTTP_409_CONFLICT)
        
       if account_type == 'S':
         
         student = StudentAccount(
          user=user,
          difficulty=difficulty
         )
         
         student.save()
       else:
         
         teacher = TeachersAccount(
          user=user,
          phone_num=phone_num,
          whatsapp_link=whatsapp_link,
          address=address,
          educational_level=educational_level
         )
         
         teacher.save()
        
       return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
       
   except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_question(request, id: str):
 try:
  
  if not id:
   return Response({'data':{},'message':'Missing required parameter'},status=HTTP_404_NOT_FOUND)
  
  try:
   
   question = Question.objects.get(id=id) 
   
   question_serializer = QuestionSerializer(question)
   
   return Response({'data':question_serializer.data,'message':'OK'},status=HTTP_200_OK)
   
  except Question.DoesNotExist:
   return Response({'data':{},'message':'Question with this id does not exist'},status=HTTP_404_NOT_FOUND,)
  
 except Exception as e:
  return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_quiz_questions(request, id: str):
    try:
        user: User = request.user
        anonymous_id = request.query_params.get('anonymous_id', '')
        # Make sure the quiz user wants to get its question exist
        try:
            quiz = get_object_or_404(Quiz, id=id)
        except Quiz.DoesNotExist:
            return Response({'data':{},"message":"Quiz with this ID does not exists."},status=HTTP_404_NOT_FOUND)
        
        
        # Locate the user tracker for that quiz, this shows that user has click the start button
        if user.is_authenticated:
            tracker = AttemptedQuizOfUser.objects.filter(quiz=quiz, attempted_by__user=user)
            quiz_tracker = tracker.exists()
            questions_answered = tracker.first().questions_answered_by_student.count()
        else:
            tracker = AttemptedQuizByAnonymousUser.objects.filter(quiz=quiz, attempted_by__anonymous_id=anonymous_id)
            quiz_tracker = tracker.exists()
            questions_answered = tracker.filter(user_answer__gt=0).count()


        
        if not quiz_tracker:
            return Response({'data':{},"message":'Unable to locate your tracker, Please Click on start quiz button'},status=HTTP_404_NOT_FOUND)
        
        total_questions = Question.objects.filter(quiz_id=quiz).count()
        
        id_limits = 5 if not user.is_authenticated else total_questions
        
        # Get all the questions related to this Quiz [IDs]
        questions_ids = Question.objects.filter(quiz_id=quiz).values_list('id', flat=True)[:id_limits]

        data = UUIDListSerializer(data={'uuids': questions_ids})
        
        print(data)

        if not data.is_valid():
            return Response({'data':{},"message": str(data.error_messages)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
        
        questions_remaining = False
        
        if not user.is_authenticated: questions_remaining = total_questions > id_limits
        
        
        return Response({'data':{'ids': data.data['uuids'], 'questions_remaining': questions_remaining, 'questions_answered': questions_answered },'message':'OK'},status=HTTP_200_OK)


    except Exception as e:
        return Response({'data':{},"message":str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def mark_user_question(request):
    from .helpers import check_quiz_time
    try:
        data = request.data
        user_answer = data.get('user_answer')
        question_id = data.get('question_id')
        anonymous_id = data.get('anonymous_id','')
        
        
        user:User | None = request.user
        editted = False
        
        #First get the associated quiz of the question
        try:
            question = Question.objects.get(id=question_id)
            quiz = Quiz.objects.get(id=question.quiz_id.id)
        except Question.DoesNotExist or Quiz.DoesNotExist:
            return Response({'data':{},'message':'Question with this ID not found'},status=HTTP_404_NOT_FOUND)
        
        # Before marking the user question check if the user is using assign time by the tutor
        if bool(quiz.time_limit): check_quiz_time(quiz=quiz, anonymous_id=anonymous_id, user=user)
        
        
        if not user.is_authenticated:
          
            quiz_tracker = AttemptedQuizByAnonymousUser.objects.filter(
                Q(attempted_by__anonymous_id=anonymous_id) & Q(quiz=quiz)
            )

            # If user has completed the quiz no need to mark question again
            if AnonymousUser.objects.get(anonymous_id=anonymous_id).completed_quiz.filter(id=quiz.id).exists():
                return Response({'data':{},'message':'Cannot remark question, you already completed this quiz'},status=HTTP_409_CONFLICT)

            if not quiz_tracker.first():
                return Response({'data':{},'message':'Unable to locate your quiz tracker'},status=HTTP_404_NOT_FOUND)
            
       
            has_user_attempted_question = quiz_tracker.filter(Q(question__id=question_id) & Q(user_answer__gt=0)
            ).values('user_answer').first()
            has_user_attempted_question = has_user_attempted_question['user_answer'] if has_user_attempted_question is not None else False

        else:
            
            quiz_tracker = get_object_or_404(AttemptedQuizOfUser, attempted_by__user=user, quiz=quiz)

            print(quiz_tracker)

            # If the quiz has been completed no need to remark the question
            if quiz_tracker.is_completed:
                return Response({'data':{},'message':'Cannot remark question, you already completed this quiz'}, status=HTTP_409_CONFLICT)


            user_answers:List = quiz_tracker.answers
            
            has_user_attempted_question = next(filter(lambda x: x['question_id'] == question_id, user_answers), None)
        #If the type is mark on click then there is no need for user to answer twice
     
        if quiz.result_display_type == quiz.ResultDisplayType.ON_COMPLETE and bool(has_user_attempted_question):
            return Response({'data':{},'message':'You already answered this question'},status=HTTP_409_CONFLICT)
        else:
            mark_quiz(
                question_id=question_id,
                user_answer=user_answer,
                quiz_tracker=quiz_tracker.first() if not user.is_authenticated else quiz_tracker,
                auth=request.user.is_authenticated
            )
        
        #If the type is different from above then user can modify answer
        if quiz.result_display_type == quiz.ResultDisplayType.ON_SUBMIT:

                if request.user.is_authenticated:
                    for item in quiz_tracker.answers:
                        if item['question_id'] == str(question.id):
                             # Update the user_answer for the matching question_id
                            item['user_answer'] = user_answer
                        #Save the updated quiz_tracker
                    quiz_tracker.save()
                else:
                    anonymous_user = AnonymousUser.objects.get(anonymous_id=anonymous_id)
                    quiz_tracker, created = AttemptedQuizByAnonymousUser.objects.get_or_create(attempted_by=anonymous_user, quiz=quiz, question=question, defaults={
                        'user_answer':user_answer,
                    })
                    
                    if not created:
                        editted = quiz_tracker.user_answer != user_answer
                        quiz_tracker.user_answer = user_answer
                        quiz_tracker.save()  
        
        result = evaluate_user_answer(question, user_answer)

        show_answer = quiz.result_display_type == quiz.ResultDisplayType.ON_COMPLETE
        correct_answer = result['correct_answer'] if show_answer else None
        is_correct = result['is_correct'] if show_answer else None
        
        data = {'show_answer': show_answer,'correct_answer': correct_answer,'is_correct':is_correct,'question_type':question.question_type, 'editted': editted}
        
        return Response({'data':data,'message':'OK'},status=HTTP_200_OK)

    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@transaction.atomic()
def get_quiz_result(request):
 try:
  
  user:User=request.user
  data = request.query_params
  quiz_id = data.get('quiz_id')
  anonymous_id = data.get('anonymous_id', '')
  ip_address = data.get('ip_address', get_client_ip(request)[0])
  
  wrong_answer_count = 0
  corrections = []
  
  try:
    quiz = get_object_or_404(Quiz, id=quiz_id)
  except Quiz.DoesNotExist:
      return Response({'data':{},'message':"Either you have not start this quiz or quiz does not exist"}, status=HTTP_404_NOT_FOUND)
  
  total_question = Question.objects.filter(quiz_id=quiz).count()
  expected_xp = Question.objects.filter(quiz_id=quiz).aggregate(expected_xp=models.Sum('question_point')).get('expected_xp', None)
  
  if user.is_authenticated:
        student = get_object_or_404(StudentAccount, user=user)
        quiz_tracker = get_object_or_404(AttemptedQuizOfUser, attempted_by=student, quiz=quiz)
        
        user_answers: list = quiz_tracker.answers
        questions_attempted = quiz_tracker.questions_answered_by_student.count()
        
        
        score_board, created = ScoreBoard.objects.get_or_create(
            user=student,
            quiz=quiz,
            defaults={
                'user': student,
                'quiz': quiz,
                'xp_earn': quiz_tracker.XP,
                'start_time': quiz_tracker.created_at,
                'end_time': timezone.now(),
                'attempted_question': questions_attempted,
                'expected_xp': expected_xp,
                'total_question': total_question,
                'feedback': give_user_feedback(quiz_tracker.XP, expected_xp),
            }
        )
        
        if not created:
            data = create_result_response_data(score_board, total_question)
            serialized_data = ResultSerializer(data=data)

            if not quiz_tracker.is_completed:
                quiz_tracker.is_completed = True
                quiz_tracker.save()

            if not serialized_data.is_valid():
                return Response({'data':{},'message':str(serialized_data.error_messages)},status=HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({'data':serialized_data.data,'message':'OK'},status=HTTP_200_OK)
            
        #check for wrong answers
        for i in range(total_question):
            
            question = Question.objects.get(id=user_answers[i]['question_id'])
            result = evaluate_user_answer(question, user_answers[i]['user_answer'] or '')
            
            if not result['is_correct']:
                wrong_answer_count += 1
                correct_answer = {'question': question.question_body, 'correct_answer': question.correct_answer_explanation}
                corrections.append(correct_answer)
      
        score_board.wrong_answers = wrong_answer_count
        score_board.corrections = corrections
        score_board.xp_earn = quiz_tracker.XP
        score_board.start_time = quiz_tracker.created_at
        score_board.save()
      
        quiz_tracker.is_completed = True
        quiz_tracker.save()

        # Notify the user that the quiz is completed
        notification_helper(
            user,
            f'You just completed {quiz.title}, congratulations',
            Notifications.NotificationType.DEFAULT
        )
        
        data = create_result_response_data(score_board, total_question)
        serialized_data = ResultSerializer(data=data)
            
        if not serialized_data.is_valid():
            return Response({'data':{},'message':str(serialized_data.errors)},status=HTTP_500_INTERNAL_SERVER_ERROR)
            
        return Response({'data':serialized_data.data,'message':'OK'},status=HTTP_200_OK)
  else:
    #  Find the anonymous user'
    anonymous_user = AnonymousUser.objects.filter(
        Q(anonymous_id=anonymous_id) | Q(ip_address=ip_address)
    ).first()
    
    if not anonymous_user:
        return Response({'data':{},'message':''},status=HTTP_404_NOT_FOUND)
    
    quiz_tracker = AttemptedQuizByAnonymousUser.objects.filter(
        Q(attempted_by=anonymous_user) & Q(quiz=quiz)
    ).all()
    
    if quiz_tracker.count() == 0:
        return Response({'data':{},'message':"You have'nt attempt this quiz."},status=HTTP_400_BAD_REQUEST)
    
    for i in range(total_question):
        
        if i == quiz_tracker.count():
            break
        
        result = evaluate_user_answer(quiz_tracker[i].question, quiz_tracker[i].user_answer)
        
        if not result['is_correct']:
            wrong_answer_count += 1
            correct_answer = {'question':quiz_tracker[i].question.question_body, 'correct_answer':quiz_tracker[i].question.correct_answer_explanation}
            corrections.append(correct_answer)
            
    xp_earn = quiz_tracker.aggregate(xp_earn=models.Sum('xp_earn')).get('xp_earn', 0)
    
    #Add all the scores together
    feedback = give_user_feedback(xp_earn, expected_xp)
    start_time = quiz_tracker.order_by('created_at').values('created_at').first().get('created_at', timedelta(minutes=10))
    end_time = quiz_tracker.order_by('created_at').values('created_at').last().get('created_at', timedelta(minutes=10))
    attempted_questions = AttemptedQuizByAnonymousUser.objects.filter(
        Q(attempted_by=anonymous_user) & Q(user_answer__gt=0) & Q(quiz=quiz)
    ).count()
    
    anonymous_user.xp = xp_earn
    anonymous_user.completed_quiz.add(quiz)
    anonymous_user.save()
    
    
    #Mark quiz as completed
    data ={'feedback':feedback,'corrections':corrections, 'attempted_questions': attempted_questions,'start_time':start_time,'wrong_answers':wrong_answer_count,'xp_earn':xp_earn, 'total_questions':total_question, 'expected_xp':expected_xp,'end_time':end_time}
    serializer = ResultSerializer(data=data)
    
    if not serializer.is_valid():
        return Response({'data':{},'message':str(serializer.errors)},status=HTTP_500_INTERNAL_SERVER_ERROR)
    #Result to display to user will contain --> Their Score, Total Questions, Questions They Attempted, Questions They Failed, Questions They Got Correct, Time They Used and Time remaining for them
  
    return Response({'data':serializer.data,'message':'OK'},status=HTTP_200_OK)
  
 except Exception as e:
  return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
 
@api_view(['POST'])
def retake_a_quiz(request):
    try:
        data = request.data
        quiz_id = data.get('quiz_id')
        anonymous_id = data.get('anonymous_id', '')
        ip_address = data.get('ip_address', '123.129.00')
        user = request.user

        # Check if the user is authenticated or not
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        if not quiz.allow_retake:
            return Response({'data':{},'message':'This quiz does not allow retakes'}, status=HTTP_401_UNAUTHORIZED)

        if user.is_authenticated:
            # Find the tracker and delete it if the user wants to try again
            quiz_tracker = AttemptedQuizOfUser.objects.get(quiz=quiz, attempted_by__user=user)
            get_object_or_404(ScoreBoard, quiz=quiz, user=quiz_tracker.attempted_by).delete()
            
            quiz_tracker.attempted_by.xp -= quiz_tracker.XP            
            
            quiz_tracker.attempted_by.save()
            
            quiz_tracker.delete()
            response_message = 'Authenticated user attempt cleared.'
        else:
            AttemptedQuizByAnonymousUser.objects.filter(
                Q(quiz=quiz) & Q(attempted_by__anonymous_id=anonymous_id)
            ).delete()
            #Find the quiz that was mark as completed then remove it 
            AnonymousUser.objects.get(anonymous_id=anonymous_id).completed_quiz.remove(quiz)
            response_message = 'Anonymous user attempt cleared.'

        return Response({'data': {}, 'message': response_message}, status=HTTP_200_OK)

    except Quiz.DoesNotExist:
        return Response({'data': {}, 'message': 'Quiz with this ID does not exist'}, status=HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment_to_quiz(request):
    user:User = request.user
    
    data = request.data
    quiz_id = data['quiz_id']
    comment = data['comment']
    
    try:
        #First run model to avoid abuse or incensitive comment
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        comment = Comments(
            user=user,
            body=comment,
            quiz=quiz
        )
        
        comment.save()
        data = CommentsSerializer(comment)
        return Response({'data':data.data, 'message':'OK'},status=HTTP_200_OK)
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def quiz_timer(request, quiz_id: str):
    from .helpers import check_quiz_time
    try:
        data = request.query_params 

        anonymous_id =  data.get('anonymous_id', None)
        anonymous_id = anonymous_id if anonymous_id else None
        user:User = request.user

    	# After checking if the user is online or not find the quiz they are attending and the tracker
        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'data':{},'message':"Quiz with this ID does not exist"}, status=HTTP_404_NOT_FOUND)
        
        quiz_duration = quiz.time_limit#The duration like time set by the tutor to finish quiz

        # First check if the quiz is time-base quiz else do nothing 
        if not bool(quiz_duration):
            return Response({'data':{},'message':'No time is assign to this quiz'},status=HTTP_200_OK)

        remaining_time = check_quiz_time(quiz=quiz, anonymous_id=anonymous_id, user=user)
            
        # Time is still remaining for user just send back remaining time :)
        return Response({'data':{'time_remaining':remaining_time * 60}, 'message':'OK'},status=HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_quiz_details(request, id):
    try:
        data = request.query_params
        anonymous_id = data.get('anonymous_id', '')
        user: User = request.user

        quiz = get_object_or_404(Quiz, id=id)
        anonymous_user = None

        if not user.is_authenticated:
            try:
                anonymous_user = AnonymousUser.objects.get(anonymous_id=anonymous_id)
                is_completed = anonymous_user.completed_quiz.filter(id=quiz.id).exists()
            except AnonymousUser.DoesNotExist:
                return Response({'data':{},'message':'Could not locate anonymous user with this ID'}, status=HTTP_404_NOT_FOUND)
        else:

            is_completed = False

            student = get_object_or_404(StudentAccount, user=user)
            quiz_tracker = AttemptedQuizOfUser.objects.filter(attempted_by=student, quiz=quiz).first()

            if quiz_tracker: is_completed = quiz_tracker.is_completed
            

        has_started = has_started_quiz(
            anonymous_user = anonymous_user or None,
            user=user,
            quiz=quiz,
            auth=user.is_authenticated
        )


        data = QuizSerializer(quiz, context={'has_user_started_quiz': has_started, 'is_completed': is_completed})

        return Response({'data':data.data, 'message':'OK'},status=HTTP_200_OK)
        
    except Exception as e:
        return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_question(request):
    try:
        data = request.data

        quiz_id = data['quiz_id']
        question_id = data['question_id']
        issue = data['issue']

        user:User = request.user

        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            question = get_object_or_404(Question, id=question_id)
        except Quiz.DoesNotExist or Question.DoesNotExist:
            return Response({'data':{},'message':''}, status=HTTP_404_NOT_FOUND)
        
        
        # Check if user has already reported this question
        if QuizReports.objects.filter(quiz=quiz, question=question, user=user).exists():
            return Response({'data':{},'message':'You already reported this Question'},status=HTTP_409_CONFLICT)

        
        report = QuizReports(
            user=user,
            quiz=quiz,
            question=question,
            issue=issue
        )

        report.save()

        return Response({'data':{},"message":"This question has been reported"},status=HTTP_200_OK)


    except Exception as e:
        return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quiz_related_to_user(request):
    try:
        user: User = request.user
        data = request.query_params

        keyword = data.get('keyword', '')

        # Check if the user is a tutor or student
        try:
            student = get_object_or_404(StudentAccount, user=user)

            if not student: tutor = get_object_or_404(TeachersAccount, user=user)

        except StudentAccount.DoesNotExist or TeachersAccount.DoesNotExist:
            return Response({'data':{},'message':'Unable to locate user.'}, status=HTTP_404_NOT_FOUND)
        
        # Find the quizzes related to this user i.e quiz attempted by the user
        if student:
            quizzes = AttemptedQuizOfUser.objects.filter(
                Q(attempted_by=student) & Q(quiz__title__icontains=keyword)
            ).values('quiz__id', 'quiz__title')[:7]
            serializer = RelatedQuizSerializer(quizzes, many=True)

        if not student and tutor:
            quizzes = Quiz.objects.filter(
                Q(host=user) & Q(title__icontains=keyword)
            ).values('id', 'title')[:7]
            serializer = RelatedQuizSerializerForTutor(quizzes, many=True)

        # Now i know i got similar data types i.e UUID and STR so send a response
        return Response({'data':serializer.data,'message':'OK'},status=HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class NotificationApi(APIView):
    def get(self, request):
        try:
            data = request.query_params
            size = int(data.get('size', 10))
            user: User = request.user
            notifications = Notifications.objects.filter(user=user, is_read=False)[:size]
            notifications_serializer = NotificationSerializer(notifications, many=True)

            return Response({'data':notifications_serializer.data,'message': 'OK'},status=HTTP_200_OK)
        except Exception as e:
            return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        user: User = request.user

        Notifications.objects.filter(is_read=False, user=user).all().update(is_read=True)

        return Response({'data':{},',message':'OK'},status=HTTP_200_OK)

    # This is to mark single the notifications as read
    def patch(self, request):
        data = request.data
        id = data['id']

        notification = Notifications.objects.filter(id=id, is_read=False).first()

        if notification:
            notification.is_read = True
            notification.save()

        return Response({'data':{},',message':'OK'},status=HTTP_200_OK)

@permission_classes([IsAuthenticated])
class SavedQuizAPI(APIView):
 def get(self, request):
    try:
        quiz_id = request.query_params['quiz_id']
        user:User = request.user
        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
        is_saved = SavedQuiz.objects.filter(quiz=quiz, user=user).exists()

        return Response({'data':{'is_saved': is_saved},"message":"OK"}, status=HTTP_200_OK)

    except Exception as e:
        return Response({'data':{},"message":str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# This Function Saved and Unsave
 def post(self, request):
    try:
        data = request.data

        user:User = request.user
        quiz_id = data['quiz_id']

        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        


        saved_quiz, created = SavedQuiz.objects.get_or_create(quiz=quiz, user=user, defaults={
            "quiz": quiz,
            "user": user
        })

        if not created:
            saved_quiz.delete()

        message = "Quiz Saved" if created else "Quiz Removed From Saved"

        return Response({'data':{},"message":message},status=HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({'data':{},"message": str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class RatingsAPI(APIView):
    def get(self, request):
        try:
            user = request.user
            data = request.query_params
            action = data.get('action')
            obj_id = data.get('id')

            if action not in [Ratings.RatingsType.Quiz, Ratings.RatingsType.TEACHER]:
                return Response({'data': {}, 'message': 'Invalid action call'}, status=HTTP_400_BAD_REQUEST)

            if action == Ratings.RatingsType.Quiz:
                data_exists = Ratings.objects.filter(quiz__id=obj_id, user=user).exists()
            else:
                data_exists = Ratings.objects.filter(teacher__id=obj_id, user=user).exists()

            return Response({'data': data_exists, 'message': 'OK'}, status=HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            data = request.data
            obj_id = data.get('id')
            action = data.get('action')

            user = request.user

            if action not in [Ratings.RatingsType.Quiz, Ratings.RatingsType.TEACHER]:
                return Response({'data': {}, 'message': 'Invalid action call'}, status=HTTP_400_BAD_REQUEST)

            if action == Ratings.RatingsType.Quiz:
                obj = get_object_or_404(Quiz, id=obj_id)
            else:
                obj = get_object_or_404(TeachersAccount, id=obj_id)

            rating, created = Ratings.objects.get_or_create(
                user=user,
                defaults={'type': action, 'quiz': obj} if action == Ratings.RatingsType.Quiz
                        else {'type': action, 'teacher': obj}
            )

            if not created:
                rating.delete()

            message = f"{obj._meta.verbose_name.capitalize()} rated" if created else f"{obj._meta.verbose_name.capitalize()} has been unrated"

            return Response({'data': {}, 'message': message}, status=HTTP_200_OK)

        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class CommentAPI(APIView):
 def get(self, request):
    try:
        comment_id = request.query_params['comment_id']
        user:User = request.user
        try:
            comment = get_object_or_404(Comments, id=comment_id)
        except Quiz.DoesNotExist:
            return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
        is_liked = comment.likes.filter(id=user.id).exists()

        return Response({'data':{'is_liked': is_liked},"message":"OK"}, status=HTTP_200_OK)

    except Exception as e:
        return Response({'data':{},"message":str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# This Function Like and unlike comment
 def post(self, request):
    try:
        data = request.data

        user:User = request.user
        comment_id = data['comment_id']

        try:
            comment = get_object_or_404(Comments, id=comment_id)
        except Quiz.DoesNotExist:
            return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
        is_liked = comment.likes.filter(id=user.id).exists()

        if is_liked:
            comment.likes.remove(user)
            comment.save()
        else:
            comment.likes.add(user)
            comment.save()

        message = ''

        if is_liked: message = "Comment liked"

        return Response({'data':{},"message":message},status=HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({'data':{},"message": str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class FeatureWaitListAPI(APIView):
    
    def post(self, request):
        
        try:
            user: User = request.user
            data = request.data
            feature_name = data['feature_name']

            if feature_name not in FeatureWaitList.Features.labels:
                return Response({'data':{}, 'message':'BAD REQUEST'}, status=HTTP_400_BAD_REQUEST)
        
            wait_list = FeatureWaitList(
                user=user,
                feature_name=feature_name
            )
            message = f"Thanks for your interest in our new feature! You've successfully joined the wait-list. We'll send an email notification to your address {user.email} once the feature becomes available." if user.email else "Thanks for your interest in our new feature! You've successfully joined the wait-list. To receive a notification email when the feature is available, please update your email address in your account settings."
            # Upon saving this will check if the user is already on the wait list 
            wait_list.save()
            return Response({'data':{},'message':message}, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get(self, request):
        try:
            
            user:User = request.user
            feature_name = request.query_params['feature_name']
            
            is_on_wait_list = FeatureWaitList.objects.filter(feature_name=feature_name, user__id=user.id).exists()
            
            return Response({'data':{'is_on_wait_list': is_on_wait_list}}, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
    
