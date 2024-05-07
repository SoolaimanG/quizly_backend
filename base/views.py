from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

import os
import uuid

from .models import User, ForgetPassword, EmailVerification, StudentAccount, TeachersAccount,Category, Notifications, FeatureWaitList
from rest_framework.response import Response
from rest_framework.decorators import permission_classes,api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import password_validation
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR,HTTP_400_BAD_REQUEST, HTTP_429_TOO_MANY_REQUESTS,HTTP_409_CONFLICT
from .helpers import generate_otp,send_email, generate_random_email,generate_random_password, notification_helper
from emails import otp_message, verify_email_address
from serializers import UserSerializer, CategorySerializer, NotificationSerializer, TeachersAccountSerializer, StudentAccountSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Q

from helpers import image_uploader


from permissions import IsPostAuthenticatedOnly

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
        if not username or not password:
            return Response({'data':{},'message':"Missing required fields username or password"}, status=HTTP_400_BAD_REQUEST)
        
        #Password is neccesary but in the case where the user whats to login the app using oauth the password will not be provided so not happens execept for Local auth password is required.
        
        generated_password = generate_random_password(35)
        
        user = User.objects.filter(username=username) #Loockup the user in the database and if it exists confirm credentials

        if not user.exists() and not bool(create_new_account):
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
        token.set_exp(lifetime=timedelta(hours=24))
        
        #Notify the user about the new password created for them in case the want to login using L i.e Local Authentication
        data = UserSerializer(__)
        __data = {
        'password': generated_password if created and __.auth_provider != 'L' else '',
        'access_token': str(token.access_token),
        }
        
        __.save() #Save the user as first-timeer if the created is true and then false it means that the user is already in the database
        
        return Response({'data':{**__data, **data.data},'message':f"{__.username.capitalize()} logged in successfully"}, status=HTTP_200_OK)
    
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
          
            data = request.data
            profile_image = image_uploader(data.get('profile_image', ''))
            
            user_data = None
            
            if profile_image:
                user_data = {
                **data,
                'profile_image': profile_image or None,
                }
            else:
                user_data = {
                    **data
                }
                
            data = UserSerializer(instance=user, data=user_data, partial=True)
            if data.is_valid():
                user.save()
                return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
            else:
                return Response({'data':{},'message': str(data.errors)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
            
      except Exception as e:
          print(e)
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
         
         user = User.objects.get(id=email_verify.user.id)
         user.email_verified = True
         
         user.save()
         email_verify.delete()
         
         return Response({'data':{},'message': f'Your email has been successfully verified. Thank you {str(email_verify.user.username.capitalize())}'}, status=HTTP_200_OK)
         
      except Exception as e:
         return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
      
   permission_classes([IsAuthenticated])
   def post(self, request):
    try:
        
        data = request.data
        
        email = data['email']
        print(email)
        email = email.strip()
        user: User = request.user
        
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
        
        user.email = email
        
        user.save()
        email_verify.save()
        return Response({'data': {}, 'message': "Email verification link sent to your email address"},
                        status=HTTP_200_OK)

    except Exception as e:
        return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class TutorAccountAPI(APIView):
    def get(self, request):
        try:
            user:User = request.user
            try:
                tutor = get_object_or_404(TeachersAccount, user__id=user.id)
            except Exception as e:
                return Response({'data':{'error':'not-found'},'message': str(e)}, status=HTTP_404_NOT_FOUND)
            
            
            data = TeachersAccountSerializer(tutor)
            
            return Response({'data': data.data, 'message':'OK'}, status=HTTP_200_OK)
            
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
    def patch(self, request):
        try:
            user:User = request.user
            tutor = get_object_or_404(TeachersAccount, user__id=user.id)
            data = request.data
            
            data = TeachersAccountSerializer(instance=tutor, data=data, partial=True)
            if data.is_valid():
                data.save()
                return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
            else:
                return Response({'data':{},'message':str(data.errors)}, status=HTTP_429_TOO_MANY_REQUESTS)
            
            return
        except Exception as e:
            return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class StudentAccountAPI(APIView):
    def get(self, request):
        try:
            user: User = request.user
            student = get_object_or_404(StudentAccount, user__id=user.id)
            data = StudentAccountSerializer(student)
            
            return Response({'data':data.data,'message':'OK'}, status=HTTP_200_OK)
        except Exception as e:
            return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

class CategoryAPI(APIView):
    def get(self, request):
        try:
            user: User = request.user
            
            categories = Category.objects.all()
        
            serializer = CategorySerializer(categories, many=True)
            serialized_data = serializer.data
        
            return Response({'data':serialized_data,'message':"OK"},status=HTTP_200_OK)
        except Exception as e:
            return Response({'data':{},'messages':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

    permission_classes([IsAuthenticated])
    def post(self, request):
        try:
            data = request.data
            user:User = request.user
            
            subjects = []
            
            for i in data['favourites']:
                category = Category.objects.get(body=i)
                subjects.append(category)
            
            if user.account_type == user.AccountType.TEACHER:
                tutor = get_object_or_404(TeachersAccount, user__id=user.id)
                tutor.specializations.set(subjects)
            
            if user.account_type == user.AccountType.STUDENT:
                student = get_object_or_404(StudentAccount, user__id=user.id)
                student.favourites.set(subjects)
                
            
            return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
            
            
        except Exception as e:
            print(e)
            return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

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




 
# @api_view(['POST'])
# def retake_a_quiz(request):
#     try:
#         data = request.data
#         quiz_id = data.get('quiz_id')
#         anonymous_id = data.get('anonymous_id', '')
#         ip_address = data.get('ip_address', '123.129.00')
#         user = request.user

#         # Check if the user is authenticated or not
#         quiz = get_object_or_404(Quiz, id=quiz_id)
        
#         if not quiz.allow_retake:
#             return Response({'data':{},'message':'This quiz does not allow retakes'}, status=HTTP_401_UNAUTHORIZED)

#         if user.is_authenticated:
#             # Find the tracker and delete it if the user wants to try again
#             quiz_tracker = AttemptedQuizOfUser.objects.get(quiz=quiz, attempted_by__user=user)
#             get_object_or_404(ScoreBoard, quiz=quiz, user=quiz_tracker.attempted_by).delete()
            
#             quiz_tracker.attempted_by.xp -= quiz_tracker.XP            
            
#             quiz_tracker.attempted_by.save()
            
#             quiz_tracker.delete()
#             response_message = 'Authenticated user attempt cleared.'
#         else:
#             AttemptedQuizByAnonymousUser.objects.filter(
#                 Q(quiz=quiz) & Q(attempted_by__anonymous_id=anonymous_id)
#             ).delete()
#             #Find the quiz that was mark as completed then remove it 
#             AnonymousUser.objects.get(anonymous_id=anonymous_id).completed_quiz.remove(quiz)
#             response_message = 'Anonymous user attempt cleared.'

#         return Response({'data': {}, 'message': response_message}, status=HTTP_200_OK)

#     except Quiz.DoesNotExist:
#         return Response({'data': {}, 'message': 'Quiz with this ID does not exist'}, status=HTTP_404_NOT_FOUND)

#     except Exception as e:
#         return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)


# @api_view(['GET'])
# def quiz_timer(request, quiz_id: str):
#     from .helpers import check_quiz_time
#     try:
#         data = request.query_params 

#         anonymous_id =  data.get('anonymous_id', None)
#         anonymous_id = anonymous_id if anonymous_id else None
#         user:User = request.user

#     	# After checking if the user is online or not find the quiz they are attending and the tracker
#         try:
#             quiz = get_object_or_404(Quiz, id=quiz_id)
#         except Quiz.DoesNotExist:
#             return Response({'data':{},'message':"Quiz with this ID does not exist"}, status=HTTP_404_NOT_FOUND)
        
#         quiz_duration = quiz.time_limit#The duration like time set by the tutor to finish quiz

#         # First check if the quiz is time-base quiz else do nothing 
#         if not bool(quiz_duration):
#             return Response({'data':{},'message':'No time is assign to this quiz'},status=HTTP_200_OK)

#         remaining_time = check_quiz_time(quiz=quiz, anonymous_id=anonymous_id, user=user)
            
#         # Time is still remaining for user just send back remaining time :)
#         return Response({'data':{'time_remaining':remaining_time * 60}, 'message':'OK'},status=HTTP_200_OK)

#     except Exception as e:
#         print(e)
#         return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(['GET'])
# def get_quiz_details(request, id):
#     try:
#         data = request.query_params
#         anonymous_id = data.get('anonymous_id', '')
#         user: User = request.user

#         quiz = get_object_or_404(Quiz, id=id)
#         anonymous_user = None

#         if not user.is_authenticated:
#             try:
#                 anonymous_user = AnonymousUser.objects.get(anonymous_id=anonymous_id)
#                 is_completed = anonymous_user.completed_quiz.filter(id=quiz.id).exists()
#             except AnonymousUser.DoesNotExist:
#                 return Response({'data':{},'message':'Could not locate anonymous user with this ID'}, status=HTTP_404_NOT_FOUND)
#         else:

#             is_completed = False

#             student = get_object_or_404(StudentAccount, user=user)
#             quiz_tracker = AttemptedQuizOfUser.objects.filter(attempted_by=student, quiz=quiz).first()

#             if quiz_tracker: is_completed = quiz_tracker.is_completed
            

#         has_started = has_started_quiz(
#             anonymous_user = anonymous_user or None,
#             user=user,
#             quiz=quiz,
#             auth=user.is_authenticated
#         )


#         data = QuizSerializer(quiz, context={'has_user_started_quiz': has_started, 'is_completed': is_completed})

#         return Response({'data':data.data, 'message':'OK'},status=HTTP_200_OK)
        
#     except Exception as e:
#         return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(["POST"])
# @permission_classes([IsAuthenticated])
# def report_question(request):
#     try:
#         data = request.data

#         quiz_id = data['quiz_id']
#         question_id = data['question_id']
#         issue = data['issue']

#         user:User = request.user

#         try:
#             quiz = get_object_or_404(Quiz, id=quiz_id)
#             question = get_object_or_404(Question, id=question_id)
#         except Quiz.DoesNotExist or Question.DoesNotExist:
#             return Response({'data':{},'message':''}, status=HTTP_404_NOT_FOUND)
        
        
#         # Check if user has already reported this question
#         if QuizReports.objects.filter(quiz=quiz, question=question, user=user).exists():
#             return Response({'data':{},'message':'You already reported this Question'},status=HTTP_409_CONFLICT)

        
#         report = QuizReports(
#             user=user,
#             quiz=quiz,
#             question=question,
#             issue=issue
#         )

#         report.save()

#         return Response({'data':{},"message":"This question has been reported"},status=HTTP_200_OK)


#     except Exception as e:
#         return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_quiz_related_to_user(request):
#     try:
#         user: User = request.user
#         data = request.query_params

#         keyword = data.get('keyword', '')

#         # Check if the user is a tutor or student
#         try:
#             student = get_object_or_404(StudentAccount, user=user)

#             if not student: tutor = get_object_or_404(TeachersAccount, user=user)

#         except StudentAccount.DoesNotExist or TeachersAccount.DoesNotExist:
#             return Response({'data':{},'message':'Unable to locate user.'}, status=HTTP_404_NOT_FOUND)
        
#         # Find the quizzes related to this user i.e quiz attempted by the user
#         if student:
#             quizzes = AttemptedQuizOfUser.objects.filter(
#                 Q(attempted_by=student) & Q(quiz__title__icontains=keyword)
#             ).values('quiz__id', 'quiz__title')[:7]
#             serializer = RelatedQuizSerializer(quizzes, many=True)

#         if not student and tutor:
#             quizzes = Quiz.objects.filter(
#                 Q(host=user) & Q(title__icontains=keyword)
#             ).values('id', 'title')[:7]
#             serializer = RelatedQuizSerializerForTutor(quizzes, many=True)

#         # Now i know i got similar data types i.e UUID and STR so send a response
#         return Response({'data':serializer.data,'message':'OK'},status=HTTP_200_OK)

#     except Exception as e:
#         print(e)
#         return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

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

# @permission_classes([IsAuthenticated])
# class SavedQuizAPI(APIView):
#  def get(self, request):
#     try:
#         quiz_id = request.query_params['quiz_id']
#         user:User = request.user
#         try:
#             quiz = get_object_or_404(Quiz, id=quiz_id)
#         except Quiz.DoesNotExist:
#             return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
#         is_saved = SavedQuiz.objects.filter(quiz=quiz, user=user).exists()

#         return Response({'data':{'is_saved': is_saved},"message":"OK"}, status=HTTP_200_OK)

#     except Exception as e:
#         return Response({'data':{},"message":str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# # This Function Saved and Unsave
#  def post(self, request):
#     try:
#         data = request.data

#         user:User = request.user
#         quiz_id = data['quiz_id']

#         try:
#             quiz = get_object_or_404(Quiz, id=quiz_id)
#         except Quiz.DoesNotExist:
#             return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        


#         saved_quiz, created = SavedQuiz.objects.get_or_create(quiz=quiz, user=user, defaults={
#             "quiz": quiz,
#             "user": user
#         })

#         if not created:
#             saved_quiz.delete()

#         message = "Quiz Saved" if created else "Quiz Removed From Saved"

#         return Response({'data':{},"message":message},status=HTTP_200_OK)

#     except Exception as e:
#         print(e)
#         return Response({'data':{},"message": str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

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

# @permission_classes([IsAuthenticated])
# class CommentAPI(APIView):
#  def get(self, request):
#     try:
#         comment_id = request.query_params['comment_id']
#         user:User = request.user
#         try:
#             comment = get_object_or_404(Comments, id=comment_id)
#         except Quiz.DoesNotExist:
#             return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
#         is_liked = comment.likes.filter(id=user.id).exists()

#         return Response({'data':{'is_liked': is_liked},"message":"OK"}, status=HTTP_200_OK)

#     except Exception as e:
#         return Response({'data':{},"message":str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

# # This Function Like and unlike comment
#  def post(self, request):
#     try:
#         data = request.data

#         user:User = request.user
#         comment_id = data['comment_id']

#         try:
#             comment = get_object_or_404(Comments, id=comment_id)
#         except Quiz.DoesNotExist:
#             return Response({'data':{},"message":"Quiz Does not exists."},status=HTTP_404_NOT_FOUND)
        
#         is_liked = comment.likes.filter(id=user.id).exists()

#         if is_liked:
#             comment.likes.remove(user)
#             comment.save()
#         else:
#             comment.likes.add(user)
#             comment.save()

#         message = ''

#         if is_liked: message = "Comment liked"

#         return Response({'data':{},"message":message},status=HTTP_200_OK)

#     except Exception as e:
#         print(e)
#         return Response({'data':{},"message": str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

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
    
    
