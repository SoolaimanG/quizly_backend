# General helper functions
from serializers import ImageSerializer
from base.models import UploadImage

from dotenv import load_dotenv
load_dotenv()
import os

def image_uploader(image) -> str:
    # Assuming ImageSerializer is a serializer for your UploadImage model
    image_serializer = ImageSerializer(data={"image": image})

    if image_serializer.is_valid():
        # Save the image instance to the database
        image_instance = UploadImage(
            image=image
        )

        image_instance.save()
        app_path = os.environ.get("QUIZLY_API_URL") + "/media/"
        # Return the path or URL of the saved image
        return app_path + str(image_instance.image)
    else:
        # Handle the case where the serializer is not valid
        raise ValueError("Unable to upload image")

def post_owner(post, user):
    if post.posted_by.id != user.id or post.community.owner.id != user.id:
        raise ValueError('You cannot edit this post')

def remove_image_path(image_url: str):
    # Define the path to the directory where images are stored
    directory_path = r"C:\Users\SULEMAN\Desktop\quizly_api\static\images"
    
    # Check if the image URL is empty or None
    if not image_url:
        return
    
    # Extract the file name from the image URL
    file_name = image_url.split('/')[-1]
    
    # Construct the full file path
    file_path = os.path.join(directory_path, file_name)
    
    # Check if the file exists before attempting to remove it
    if os.path.exists(file_path):
        os.remove(file_path)


