from rest_framework.permissions import BasePermission
from base.models import TeachersAccount

class OnlyStudentAllow(BasePermission):
 
 message = "Only students can participate in quizzes."
 
 def has_permission(self, request, view):
  
  is_teacher = TeachersAccount.objects.filter(user=request.user).exists()
  return not is_teacher