from django.contrib import admin
from .models import User, ForgetPassword, EmailVerification, StudentAccount, TeachersAccount, Category, Logs, Notifications, FeatureWaitList

# Register your models here.

admin.site.register(User)
admin.site.register(ForgetPassword)
admin.site.register(EmailVerification)
admin.site.register(StudentAccount)
admin.site.register(TeachersAccount)
admin.site.register(Category)
admin.site.register(Logs)
admin.site.register(Notifications)
admin.site.register(FeatureWaitList)
