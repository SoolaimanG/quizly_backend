from django.contrib import admin
from .models import Question, Quiz, QuizAccessToken, QuizComments, QuizSavedByUser, QuizScoreBoard, QuizzesAttemptedByUser, AttemptedQuizByAnonymousUser, AnonymousUser, MultipleChoiceOption, OpenEndedOption, UserAnswerForQuestion

admin.site.register(Question)
admin.site.register(Quiz)
admin.site.register(QuizAccessToken)
admin.site.register(QuizComments)
admin.site.register(QuizSavedByUser)
admin.site.register(QuizScoreBoard)
admin.site.register(QuizzesAttemptedByUser)
admin.site.register(AttemptedQuizByAnonymousUser)
admin.site.register(AnonymousUser)
admin.site.register(MultipleChoiceOption)
admin.site.register(OpenEndedOption)
admin.site.register(UserAnswerForQuestion)

