from django.urls import path
from . import views

urlpatterns = [
 
 #Authentication APIs
 path('auth/',views.login_or_signup,name='login_or_signup'),
 path('auth/forget-password/',views.ForgetPasswordApiView.as_view(), name='forget_password'),
 path('auth/verify-email/',views.VerifyEmailApiView.as_view(),name='verify_email'),
 path('auth/is-authenticated/',views.isUserAuthenticated,name='is_authenticated'),
 path('auth/create-student-or-teacher/',views.create_student_or_teacher_account,name='create_student_or_teacher_account'),
 
 #Get user category
 path('subject-categories/',views.get_categories, name='categories'),
 path('user-categories/',views.get_user_category, name='user_categories'),
 
 #Bases
 path('get-quizzes/',views.get_quizzes, name='get_quizzes'),
 path('trending-quiz/',views.get_trending,name='get_trending_quiz'),
 path('quiz/comments/<str:id>/',views.quiz_comments, name='quiz_comments'),
 path('start-quiz/',views.start_quiz, name='start_quiz'),
 path('get-single-question/<str:id>/',views.get_question, name='get_single_question'),
 path('get-all-question/<str:id>/',views.get_quiz_questions, name='get_all_question'),
 path('get-quiz-details/<str:id>/',views.get_quiz_details, name='get_quiz_details'),
 path('check-answer/',views.mark_user_question, name='check_answer'),
 path('get-quiz-result/',views.get_quiz_result,name='get_quiz_result'),
 path('retake-quiz/',views.retake_a_quiz,name='retake_a_quiz'),
 path('add-comment/',views.add_comment_to_quiz,name='add_comment'),
 path('check-timer/<str:quiz_id>/',views.quiz_timer,name='check-timer'),
 path('saved-quiz/',views.SavedQuizAPI.as_view(),name='saved_quiz'),
 path('ratings/',views.RatingsAPI.as_view(),name='ratings'),
 path('comment/',views.CommentAPI.as_view(),name='comment'),
 path('report-question/',views.report_question,name='report_question'),
 path('get_related_quiz/',views.get_quiz_related_to_user,name='get_related_quiz'),
 path('notifications/', views.NotificationApi.as_view(),name='notification_api'),
 path('feature-wait-list/', views.FeatureWaitListAPI.as_view(), name='features_wait_list'),
 
 
 #Authentication Required Route
 path('user/',views.UserApiView.as_view(),name='user')
]

