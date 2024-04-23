from django.contrib import admin
from .models import User, ForgetPassword, EmailVerification, StudentAccount, TeachersAccount, Category, Logs, Quiz, Question, GermanOptions, ObjectiveOptions, Comments, AttemptedQuizOfUser, AnonymousUser, AttemptedQuizByAnonymousUser, QuizAccessToken, ScoreBoard, UploadImage, SavedQuiz, Ratings, QuizReports, Notifications, FeatureWaitList

# Register your models here.

admin.site.register(User)
admin.site.register(ForgetPassword)
admin.site.register(EmailVerification)
admin.site.register(StudentAccount)
admin.site.register(TeachersAccount)
admin.site.register(Category)
admin.site.register(Logs)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Comments)
admin.site.register(GermanOptions)
admin.site.register(ObjectiveOptions)
admin.site.register(AttemptedQuizOfUser)
admin.site.register(AnonymousUser)
admin.site.register(AttemptedQuizByAnonymousUser)
admin.site.register(QuizAccessToken)
admin.site.register(ScoreBoard)
admin.site.register(UploadImage)
admin.site.register(SavedQuiz)
admin.site.register(Ratings)
admin.site.register(QuizReports)
admin.site.register(Notifications)
admin.site.register(FeatureWaitList)
