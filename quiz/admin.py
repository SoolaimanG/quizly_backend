from django.contrib import admin
from .models import Question, Quiz, QuizAccessToken, QuizComments, QuizSavedByUser, QuizScoreBoard, QuizScoreBoardManager, QuizzesAttemptedByUser, AttemptedQuizByAnonymousUser, AnonymousUser

admin.site.register(Question)
admin.site.register(Quiz)
admin.site.register(QuizAccessToken)
admin.site.register(QuizComments)
admin.site.register(QuizSavedByUser)
admin.site.register(QuizScoreBoard)
admin.site.register(QuizzesAttemptedByUser)
admin.site.register(AttemptedQuizByAnonymousUser)

