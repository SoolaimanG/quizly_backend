from rest_framework.permissions import BasePermission
from base.models import TeachersAccount

class OnlyStudentAllow(BasePermission):
 
 message = "Only students can participate in quizzes."
 
 def has_permission(self, request, view):
  
  is_teacher = TeachersAccount.objects.filter(user=request.user).exists()
  return not is_teacher


class IsPostAuthenticatedOnly(BasePermission):
    """
    Custom permission to allow only authenticated users for POST requests.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        return True 




