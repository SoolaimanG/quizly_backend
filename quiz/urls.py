from django.urls import path
from . import views

urlpatterns = [
    # Explore Page
    path('recommended-quizzes/', views.recommended_quiz),
    
    # QUIZ 
    path('start-quiz/<str:quiz_id>/', views.start_quiz),
    path('question/<str:question_id>/', views.QuestionAPI.as_view()),
    path('quiz-comments/<str:quiz_id>/', views.QuizCommentsAPI.as_view()),
    path('quiz-result/<str:quiz_id>/', views.QuizResult.as_view()),
    path('quiz-questions/<str:quiz_id>/', views.get_quiz_questions_api),
    path('quick-quiz/', views.get_quick_quiz_for_user)
]