from base.models import User, Notifications


def notify_user_on_post_activity(user: User, community, notification_type: str):
    from .models import Community, PostComments
    
    community: Community = community
    
    activity = 'commented on' if notification_type == Notifications.NotificationsType.COMMENT else 'like'
    
    message = f"{str(user.username).capitalize()} just {activity} your post."
    notification = Notifications(
         message=message,
         user=user,
         type=notification_type
    )
    notification.save()

def upload_to(instance, filename):
 return 'images/{filename}'.format(filename=filename)