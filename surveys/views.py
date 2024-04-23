
from dotenv import load_dotenv
load_dotenv()
import os

from typing import List, Dict

from rest_framework.response import Response
from rest_framework.decorators import api_view, APIView, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR

from base.models import User
from base.helpers import generate_random_letters

from helpers import image_uploader, remove_image_path


from .models import Surveys, SurveyBlockType, WelcomeScreen, ShortText, Rating, EndScreen, PhoneNumbers, Email, Number, Date, LongText, Website, RedirectWithUrl, DropDown, Choices, YesNo, PictureChoice, SurveyDesign, SurveySettings, LastUsedBlocks, SurveyLogic, UserReponse, SurveyParticipant

from .serializer import SurveySerializer, SurveyBlockSerializer, WebsiteSerializer, WelcomeScreenSerializer, RatingSerializer, RedirectWithUrlSerializer, DateSerializer, DropDownSerializer, LongTextSerializer, ShortTextSerializer, ChoicesSerializer, EmailSerializer, YesNoSerializer, NumberSerializer, PhoneNumberSerializer, EndScreenSerializer, PictureChoiceSerializer, ChoicesOptions, DropDownOpions, PictureChoice, PictureChoiceImages, PictureChoicesImageSerializer, EndScreenSocialMedia, EndScreenSocialMediaSerializer, SurveyDesignSerializer, SurveySettingsSerializer, LastUsedSerializerBlock, SurveyLogicSerializer

from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.translation import gettext as _
from django.db.models import Max, Q

from base.helpers import send_email


from uuid import uuid4

class GenerateSurveyType():
   FEEDBACK = 'FeedBack',_('feedback')
   CONTACT = 'Contact', _('contact')
   POLL = 'Poll', _('poll')
   REGISTRATION = 'REGISTRATION',_('registration')
   REQUEST = 'Request', _('request')

block_models = {
        'PhoneNumber': PhoneNumbers,
        'Date': Date,
        'Number': Number,
        'ShortText': ShortText,
        'LongText': LongText,
        'Choices': Choices,
        'WelcomeScreen': WelcomeScreen,
        'YesNo': YesNo,
        'EndScreen': EndScreen,
        'Rating': Rating,
        'DropDown': DropDown,
        'Email': Email,
        'PictureChoice': PictureChoice,
        'RedirectToURL': RedirectWithUrl,
        'Website': Website,
    }

block_serializer= {
        'PhoneNumber': PhoneNumberSerializer,
        'Date': DateSerializer,
        'Number': NumberSerializer,
        'ShortText': ShortTextSerializer,
        'LongText': LongTextSerializer,
        'Choices': ChoicesSerializer,
        'WelcomeScreen': WelcomeScreenSerializer,
        'YesNo': YesNoSerializer,
        'EndScreen': EndScreenSerializer,
        'Rating': RatingSerializer,
        'DropDown': DropDownSerializer,
        'Email': EmailSerializer,
        'PictureChoice': PictureChoiceSerializer,
        'RedirectToURL': RedirectWithUrlSerializer,
        'Website': WebsiteSerializer,
    }


block_models_snake_case = {
    'PhoneNumbers': 'phone_number',
    'Date': 'date',
    'Number': 'number',
    'ShortText': 'short_text',
    'LongText': 'long_text',
    'Choices': 'choices',
    'WelcomeScreen': 'welcome_screen',
    'YesNo': 'yes_no',
    'EndScreen': 'end_screen',
    'Rating': 'ratings',
    'DropDown': 'dropdown',
    'Email': 'email',
    'PictureChoice': 'picture_choice',
    'RedirectToURL': 'redirect_with_url',
    'Website': 'website',
}

dummy_questions = {
    'PhoneNumber': 'Please enter your phone number',
    'Date': 'Select a date',
    'Number': 'Enter a number',
    'ShortText': 'Enter a short text',
    'LongText': 'Enter a long text',
    'Choices': 'Select from the choices',
    'WelcomeScreen': 'Welcome to the survey',
    'YesNo': 'Yes or No question',
    'EndScreen': 'End of the survey',
    'Rating': 'Rate this item',
    'DropDown': 'Select from the dropdown',
    'Email': 'Enter your email',
    'PictureChoice': 'Choose a picture',
    'RedirectToURL': 'Redirect with URL',
    'Website': 'Enter a website URL',
}

def create_choice_options(choices: List[Dict[str,str]], choice: Choices):
      """
      The function `create_choice_options` deletes existing choices for a given `choice` and then creates
      new choices based on the input `choices` list.
   
      :param choices: The `choices` parameter is a list of dictionaries where each dictionary contains two
      key-value pairs: 'option' and 'id'. This list represents the choices that you want to create as
      options for a given `choice`
      :type choices: List[Dict[str,str]]
      :param choice: The `choice` parameter in the `create_choice_options` function is an instance of the
      `Choices` model. This parameter is used to specify which set of choices the new options will belong
      to
      :type choice: Choices
      """
    # Firstly delete all the choices that exist already.
      ChoicesOptions.objects.filter(choices=choice).all().delete()
            
      [ChoicesOptions.objects.create(choices=choice, option=i['option'], id=i['id']) for i in choices]
    
def create_surveys_design(survey:Surveys):
   try:
      design = SurveyDesign(
         survey=survey,
      )
      design.save()
   except Exception as e:
      raise e

def create_survey_settings(survey:Surveys):
   settings = SurveySettings(
      survey=survey,
   )
   settings.save()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic()
def generate_block_at_start(request):
   try:
      data = request.data
      id = data['id']
      survey_type = data['survey_type']
      
      label_content = 'This is a Description, You can edit this.'
      
      survey = get_object_or_404(Surveys, id=id)
      
      survey.name = data.get('name', survey.name)
      survey.save()
      
      # Delete all the blocks available for this survey and start afresh.
      SurveyBlockType.objects.filter(survey__id=survey.id).all().delete()
      
      # Welcome Screen Must Be Available For Every Block!
      welcome_screen = WelcomeScreen(
         message='This is the Welcome Screen',
         label='You can change this.',
         have_continue_button=True,
      )
      welcome_screen.save()
      
      """
         The function `add_end_screen` creates and saves an EndScreen object with specified attributes.
         :return: The `add_end_screen()` function is returning the `EndScreen` object that was created
         and saved within the function.
         """
      def add_end_screen():
        end_screen = EndScreen(
         button_link='http://www.google.com',
         message='This is the End Screen, (You Can Edit This).',
      )
        end_screen.save()
        return end_screen
      
      
      def create_block(question: str, block_type:str, label: str, **kwargs):
         """
         The function `create_block` creates a survey block with specified question, block type, label,
         and additional keyword arguments.
         
         :param question: The `question` parameter is a string that represents the question being asked
         in the survey block
         :type question: str
         :param block_type: The `block_type` parameter in the `create_block` function specifies the
         type of block being created in a survey. It could be a text block, multiple choice block,
         rating block, or any other type of block used in a survey
         :type block_type: str
         :param label: The `label` parameter in the `create_block` function is used to specify a label
         for the survey block being created. This label can be used to identify or categorize the block
         within the survey
         :type label: str
         """
         survey_block = SurveyBlockType(
            question=question,
            survey=survey,
            block_type=block_type,
            label=label,
            **kwargs
         )
         survey_block.save()
      

      create_block(
         question='',
         block_type=SurveyBlockType.BlockType.WelcomeScreen,
         label='',
         welcome_screen=welcome_screen,
         index=1
      )
      
      if survey_type == GenerateSurveyType.FEEDBACK[1]:
         short_text = ShortText(
            max_character=500,
         )
         ratings = Rating(
            label='Rate the product below'
         )
         
         short_text.save()
         ratings.save()
         
         create_block(
            question='What is your name?',
            block_type=SurveyBlockType.BlockType.ShortText,
            label='What is your name?',
            short_text=short_text,
            is_required=True,
            is_visible=True,
            index=2
            
         )
         create_block(
            question='What would you rate this product?',
            block_type=SurveyBlockType.BlockType.Rating,
            label='What would you rate this product?',
            ratings=ratings,
            index=3
         )
         create_block(
            question='',
            block_type=SurveyBlockType.BlockType.EndScreen,
            label=label_content,
            end_screen = add_end_screen(),
            index=4,
         )
         
      if survey_type == GenerateSurveyType.CONTACT[1]:
         
         short_text = ShortText(
            max_character=500,
            label=label_content,
         )
         short_text_2 = ShortText(
            max_character=500,
            label=label_content,
         )
         email = Email(
            check_email=True,
            label=label_content
         )
         short_text.save()
         short_text_2.save()
         email.save()
         
         create_block(
            question='Enter your FullName',
            block_type=SurveyBlockType.BlockType.ShortText,
            label=label_content,
            index=2,
            short_text=short_text
         )
         create_block(
            question='Enter your Email Address',
            block_type=SurveyBlockType.BlockType.Email,
            email=email,
            label=label_content,
            is_required=True,
            index=4
         )
         create_block(
            question='Address 1',
            block_type=SurveyBlockType.BlockType.ShortText,
            label=label_content,
            short_text=short_text_2,
            index=5
         )
         create_block(
            question='',
            label=label_content,
            block_type=SurveyBlockType.BlockType.EndScreen,
            end_screen=add_end_screen(),
            index=6
         )
      
      if survey_type == GenerateSurveyType.POLL[1]:
         choice = Choices(
            multiple_selection=True,
            vertical_alignment=False,
            randomize=True
         )
         choice_one = Choices(
            multiple_selection=True,
            vertical_alignment=False,
            randomize=True
         )
         
         choice.save()
         choice_one.save()
         end_screen = add_end_screen()
         # Create the block function
         create_block(
            question='What is your favorite color?',
            block_type='Choices',
            label='',
            index=2,
            choices=choice
         )
         create_block(
            question='Which features are most important to you in a smartphone? (Select all that apply)',
            block_type='Choices',
            label='',
            index=3,
            choices=choice_one
         )
         create_block(
            question='',
            label='',
            block_type='EndScreen',
            index=4,
            end_screen=end_screen
         )
         
         choices = [
            {
               'option':'Red',
               'id': uuid4()
            },
            {
               'option':'Blue',
               'id': uuid4()
            },
            {
               'option':'White',
               'id': uuid4()
            },
            {
               'option':'Pink',
               'id': uuid4()
            },
         ]
         choices_one = [
            {
               'option':'Long battery life',
               'id': uuid4()
            },
            {
               'option':'Powerful processor',
               'id': uuid4()
            },
            {
               'option':'Large display',
               'id': uuid4()
            },
            {
               'option':'High-quality camera',
               'id': uuid4()
            },
         ]
   
         create_choice_options(choices, choice) #Create the options
         create_choice_options(choices_one, choice_one) 
      
      if survey_type == GenerateSurveyType.REGISTRATION[1]:
         pass
      
      if survey_type == GenerateSurveyType.REQUEST[1]:
         pass
      
      return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
      
   except Exception as e:
      return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_survey_details(request, id:str):
   try:
      user:User = request.user
      survey = get_object_or_404(Surveys, id=id)
      survey_blocks = SurveyBlockType.objects.filter(survey__id=survey.id).all().order_by('index')
      user_id = request.query_params.get('surveyUserId', uuid4())
      
      if survey.status == survey.Status.PRODUCTION and user.username != survey.host.username:
         survey.check_response_limit()
         survey.check_close_date()
         
         participant, __ = SurveyParticipant.objects.get_or_create(user_id=user_id, survey__id=survey.id, defaults={
            'user_id': user_id,
            'survey':survey,
         })
         
         
         if participant.survey_is_completed:
            return Response({'data':{},'message':'Thank you for your participation, you have completed this survey'}, status=HTTP_409_CONFLICT)

         

      
      # The above code snippet is written in Python and is querying the database for survey-related
      # objects based on the survey ID. It retrieves the first `SurveyDesign`, `SurveySettings`, and
      # all `SurveyLogic` objects associated with the survey ID.
      design = SurveyDesign.objects.filter(survey__id=survey.id).first()
      survey_settings = SurveySettings.objects.filter(survey__id=survey.id).first()
      logics = SurveyLogic.objects.filter(survey__id=survey.id).all()
      
      
      design_serializer = SurveyDesignSerializer(design)
      
      
      survey_serializer = SurveySerializer(survey)
      block_serializer = SurveyBlockSerializer(survey_blocks, many=True)
      settings = SurveySettingsSerializer(survey_settings)
   
         
      logic_serializer = SurveyLogicSerializer(logics, many=True)
      
      data = {
         'survey_details': survey_serializer.data,
         'blocks': block_serializer.data,
         'design': design_serializer.data,
         'setting': settings.data,
         'logics': logic_serializer.data
      }
      
      
      return Response({'data':data,'message':'OK'},status=HTTP_200_OK)
   except Exception as e:
      return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class SurveysAPIVIEW(APIView):
   def get(self, request):
      try:
         data = request.query_params
      
         user: User = request.user
         size = data.get('size', 10)
      
         surveys = Surveys.objects.filter(host=user)[:int(size)]
      
         serializer = SurveySerializer(surveys, many=True)
      
         return Response({'data':serializer.data,'message':'OK'},status=HTTP_200_OK)
      except Exception as e:
         return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
      
      
    #  Create a workspace
   def post(self, request):
    try:
        user: User = request.user
        data = request.data

        name = data['name']
        id = data.get('id', uuid4())

        survey_already_exist = lambda: Surveys.objects.filter(name__icontains=name).exists()

        while survey_already_exist():
            name += generate_random_letters(10)
            if not survey_already_exist():
                break

        survey = Surveys(
            name=name,
            host=user,
            id=id
        )

        survey.save()
      
        create_surveys_design(survey)
        create_survey_settings(survey)
        serializer = SurveySerializer(survey)

        return Response({'data': serializer.data, 'message': 'OK'}, status=HTTP_200_OK)

    except Exception as e:
        return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

   def patch(self, request):
       try:
         data = request.data
         user:User = request.user
         survey_id = data['survey_id']
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
         
         data = SurveySerializer(instance=survey,data=data, partial=True)
         
         if data.is_valid():
            data.save()
            return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
         else:
            return Response({'data':'','message': str(data.errors)}, status=HTTP_400_BAD_REQUEST)
         
       except Exception as e:
         return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
     
   def delete(self, request):
      try:
         
         data = request.query_params
         user = request.user
         id = data['id']
         name = data['name']
         
         survey = get_object_or_404(Surveys, id=id)
         
         survey.am_i_d_owner(user)
         
         if str(name).lower() != survey.name.lower():
            return Response({'data':{},'message':'Please type the name of the survey correctly before deletion'}, status=HTTP_403_FORBIDDEN)
         
         survey.delete()
         
         return Response({'data':{},'message':f"{name} has been deleted successfully"},status=HTTP_200_OK)
         
         
      except Exception as e:
         return Response({'data':{},'message':str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)


@permission_classes([IsAuthenticated])
# The `SurveyBlocks` class in Python defines methods for handling various actions related to survey
# blocks, including adding, duplicating, deleting, and updating block data.
class SurveyBlocks(APIView):
   def post(self, request):
      try:
         data = request.data
         user: User = request.user
         survey_id = data['survey_id']
         block_type = data['block_type']
         
         
         action = data['action']
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
         
         if block_type not in block_models:
            return Response({'data':{},'message':'Invalid Block Type'}, status=HTTP_400_BAD_REQUEST)
         
         block_model = block_models[block_type]
         
         if action == 'ADD':
            new = block_model.objects.create()
            index = SurveyBlockType.objects.filter(survey__id=survey.id).count()
         
            survey_blocks = SurveyBlockType(
            survey=survey,
            question=dummy_questions[block_type],
            label='This is a label and can be changed.',
            block_type= block_type,
            index = index + 1,
            **{block_models_snake_case[block_type]: new}
         )
            survey_blocks.save()
         
         if action == 'DUPLICATE':
            block_id = data['block_id']
            id = data['id']
            block_modal = block_models[block_type]
            
            survey_block = get_object_or_404(SurveyBlockType, id=id, block_type=block_type)
            
            copied_block = block_modal.objects.filter(id=block_id)
            new_block = copied_block.first()
            new_block.id = uuid4()
            new_block.index = copied_block.first().index
            new_block.save()
            
            survey_block = SurveyBlockType(
            survey=survey,
            is_required=survey_block.is_required,
            question= survey_block.question,
            label=survey_block.label,
            index = survey_block.index + 1,
            block_type=block_type,
            **{block_models_snake_case[block_type]: new_block}
         )
         
            survey_block.save()
         
         if action == 'ADD_CHOICE':
            choices = data['choices']
            id = data['id']
            choice = get_object_or_404(Choices, id=id)
            
            create_choice_options(choices, choice)
         
         if action == 'ADD_DROPDOWN_OPTIONS':
            dropdown_options = data['dropdown_options']
            id = data['id']
            dropdown = get_object_or_404(DropDown, id=id)
            
            # Firstly delete all the choices that exist already.
            DropDownOpions.objects.filter(drop_down=dropdown).delete()
            
            [DropDownOpions.objects.create(drop_down=dropdown, body=i['body'], id=i['id']) for i in dropdown_options]
         
         if action == 'REMOVE_CHOICE':
            print('RUN')
            option_id = data['choice_id']
            print(option_id)
            
            choice = get_object_or_404(ChoicesOptions, id=option_id)
            
            choice.delete()
         
         if action == 'ADD_PICTURE_CHOICE':
            id = data['picture_id']
            picture_choice = get_object_or_404(PictureChoice, id=id)
            
            picture_choice = PictureChoiceImages(
                  picture=picture_choice,
                  url='',
                  alt_tag=data['alt_tag'],
                  name=data['name'],
                  saturation=data['saturation'],
                  contrast = data['contrast'],
                  brightness=data['brightness'],
                  blur=data['blur'],
                  x=data['x'],
                  y=data['y'],
                  rotationIndex=data['rotationIndex'],
                  id=data['id'],
                  hue=data['hue'],
                  pixelate=data['pixelate'],
                  grayscale=data['grayscale']
            )
            
            picture_choice.save()
            
         # The above code is a Python if statement checking if the variable `action` is equal to the
         # string 'CHANGE_BLOCK'. If the condition is true, the code block denoted by the triple hash
         # symbols (`
         
         return Response({'data':{},'message':'OK'},status=HTTP_200_OK)
         
         
      except Exception as e:
         return Response({'data':{},'message': str(e)},status=HTTP_500_INTERNAL_SERVER_ERROR)
      
   def delete(self, request):
    data = request.query_params
    user = request.user
    survey_id = data.get('survey_id')
    block_id = data.get('block_id')
    block_type = data.get('block_type')
    
    # Validate request data
    if not all([survey_id, block_id, block_type]):
        return Response({'message': 'Invalid request data'}, status=HTTP_400_BAD_REQUEST)

    survey = get_object_or_404(Surveys, id=survey_id)
    
    # Check ownership
    survey.am_i_d_owner(user)
    
    # Check if block type is valid
    if block_type not in block_models:
        return Response({'message': 'Invalid block type'}, status=HTTP_400_BAD_REQUEST)
    
    # Delete the block
    block_model = block_models[block_type]
    try:
        block_model.objects.get(id=block_id).delete()
        return Response({'message': 'Block deleted successfully'}, status=HTTP_200_OK)
    except block_model.DoesNotExist:
        return Response({'message': 'Block not found'}, status=HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

   def patch(self, request):
      
      try:
         
         data = request.data
         block_type = data['block_type']
         sub_block_id = data.get('sub_block_id', '')
         action_type = data.get('action_type', '')
         survey_id = data['survey_id']
         block_id = data.get('block_id', "")
         user:User = request.user
         
         survey_actions = ['is_visible', 'is_required', 'header_or_label', 'remove_choice', 'edit_picture_image', 'add_image_to_picture_choice', 'remove_picture_choice', 'add_social_media', 'edit_social_media', 'remove_social_media']
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
      
         
         if action_type and action_type not in survey_actions:
            return Response({'data':{},'message':'Invalid Request'}, status=HTTP_400_BAD_REQUEST)
         
         
         # This are the actions that update the current block data 
         if block_id:
            current_block = SurveyBlockType.objects.filter(id=block_id).first()
         
         if action_type == 'is_required':
            current_block.is_required = data['is_required']
            current_block.save()
         
         if action_type == 'is_visible':
            current_block.is_visible = data['is_visible']
            current_block.save()
            
         if action_type == 'header_or_label':
            current_block.question = data.get('question', current_block.question)            
            current_block.label = data.get('label', current_block.label)
            current_block.save()
            
         if action_type == 'remove_choice':
            choice_id = data['choice_id']
            
            choice = get_object_or_404(ChoicesOptions, id=choice_id)
            
            choice.delete()
            
            return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
         
         if action_type == 'edit_picture_image':
            instance = get_object_or_404(PictureChoiceImages, id=data['id'])
            
            data = PictureChoicesImageSerializer(
               instance=instance,
               data=data,
               partial=True
            )
            if data.is_valid():
               data.save()
               return Response({'data':{}, 'message':'OK'}, status=HTTP_200_OK)
            else:
               return Response({'data':{}, 'message': str(data.errors)}, status=HTTP_400_BAD_REQUEST)
            
         if action_type == 'add_image_to_picture_choice':
            url = data['url']
            image = data['image']
            id = data['id']
            
            
            if url: remove_image_path(url)
            
            picture_image = get_object_or_404(PictureChoiceImages, id=id)
            
            url = image_uploader(image)
            
            picture_image.url = url
            picture_image.save()
           
         if action_type == 'remove_picture_choice':
            id = data['id']
            
            picture_choice = get_object_or_404(PictureChoiceImages, id=id)
            
            if picture_choice.url:remove_image_path(picture_choice.url) 
            
            picture_choice.delete()
            
         if action_type == 'add_social_media':
            id = data['sub_block_id']
            end_screen = get_object_or_404(EndScreen, id=id)
            
            # The above Python code is iterating over a list of social media objects and checking if
            # an EndScreenSocialMedia object with the same media type exists for a specific end
            # screen. If it does not exist, a new EndScreenSocialMedia object is created with the
            # provided data (id, social media link, media type) and associated with the end screen.
            # Finally, the new EndScreenSocialMedia object is saved to the database.
            if not EndScreenSocialMedia.objects.filter(end_screen__id=end_screen.id, media_type=data['media_type']).exists():
                  social_media = EndScreenSocialMedia(
                  id=data['id'],
                  social_media_link=data['social_media_link'],
                  media_type=data['media_type'],
                  end_screen=end_screen
                  )
                  social_media.save()
            else:
               return Response({'data':{},'message':'Social media type already exists.'}, status=HTTP_409_CONFLICT)
         
         if action_type == 'edit_social_media':
            id = data['id']
            social_media = get_object_or_404(EndScreenSocialMedia, id=id)
            print(social_media)
            
            data = EndScreenSocialMediaSerializer(
               instance=social_media,
               data=data,
               partial=True
            )
            
            if data.is_valid():
               data.save()
               return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
            else:
               return Response({'data':{},'message':str(data.errors)}, status=HTTP_400_BAD_REQUEST)
         
         if action_type == 'remove_social_media':
            id = data['id']
            
            get_object_or_404(EndScreenSocialMedia, id=id).delete()
            
         if action_type in survey_actions:
            return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
         
         
         
         instance = get_object_or_404(block_models[block_type], id=sub_block_id)
      
         serializer = block_serializer[block_type](instance=instance, data=data, partial=True)
         
      
         if serializer.is_valid():
            serializer.save()
            return Response({'data':{}, 'message':'OK'}, status=HTTP_200_OK)
         else:
            return Response({'data':{}, 'message': str(serializer.errors)}, status=HTTP_400_BAD_REQUEST) 
         
      except Exception as e:
         return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def change_block_to_preferred(request, survey_id: str):
   try:
      # The code snippet is written in Python and appears to be part of a web application or API. It
      # defines a variable `user` as the current user making a request. It then retrieves a survey
      # object with a specific `id` from the database using the `get_object_or_404` function. Finally,
      # it calls a method `am_i_d_owner` on the `survey` object, passing the `user` as an argument.
      # The purpose of the `am_i_d_owner` method is to check if the user is the owner of the survey.
      user:User = request.user
      data = request.data
      
      """
         old block is a dict which consist of id, block_type, index
         new_block is a dict which consist of id, block_type
      """
      old_block = data['old_block']
      new_block = data['new_block']
      
      
     # The below code is checking if the 'block_type' key in the dictionaries `old_block` and
     # `new_block` is not present in the `block_models_snake_case` list. If either of the block types
     # is not found in the list, it returns a response with an empty data object and an empty message
     # string, indicating a bad request with a status code of 400.
      if old_block['block_type'] not in block_models_snake_case or new_block['block_type'] not in block_models_snake_case:
         return Response({'data':{},'message':''}, status=HTTP_400_BAD_REQUEST)
      
      survey = get_object_or_404(Surveys, id=survey_id)
      
      survey.am_i_d_owner(user)
      
      survey_block = SurveyBlockType.objects.filter(block_type=old_block['block_type'], id=old_block['id']).first()
      
      

      # The above code is written in Python and it is using Django's ORM to delete a SurveyBlockType
      # object from the database based on the provided ID from the `old_block` dictionary. It first
      # filters the SurveyBlockType objects by the ID and then deletes the first object that matches
      # the filter criteria.
      SurveyBlockType.objects.filter(id=old_block['id']).first().delete()
      
      # The code snippet is using the `getattr()` function in Python to dynamically access an
      # attribute of an object `survey_block` based on the value of
      # `block_models_snake_case[old_block['block_type']]`. It then retrieves the corresponding model
      # from `block_models` based on `old_block['block_type']`, and deletes the object from the
      # database using the `delete()` method.
      related_block = getattr(survey_block, block_models_snake_case[old_block['block_type']])
      
      block_models[old_block['block_type']].objects.filter(id=related_block.id).first().delete()
      
      block_model = block_models[new_block['block_type']]
      new = block_model.objects.create()
      
      # The above code is creating a new `SurveyBlockType` object and replacing the old block with
      # this new block. It is setting the `survey`, `question`, `index`, `block_type`, and additional
      # attributes based on the values from `new_block` and `block_models_snake_case`. Finally, it
      # saves the `survey_block` object.
      # Create a new block and replace the old block
      survey_block = SurveyBlockType(
         survey=survey,
         question=dummy_questions[new_block['block_type']],
         index = old_block['index'],
         block_type=new_block['block_type'],
         **{block_models_snake_case[new_block['block_type']]: new}
      )
      
      survey_block.save()
      
      return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
      
      
   except Exception as e:
      return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_survey_designs(request, survey_id: str):
   try:
      data = request.data
      user:User = request.user
      id = data['id']
      
      survey = get_object_or_404(Surveys, id=survey_id)
      
      survey.am_i_d_owner(user)
      
      instance = get_object_or_404(SurveyDesign, id=id)
      
      data = SurveyDesignSerializer(instance=instance, data=data, partial=True)
      
      if data.is_valid():
         data.save()
         return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
      else:
         return Response({'data':{},'message':str(data.errors)}, status=HTTP_400_BAD_REQUEST)
      
   except Exception as e:
      return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
   
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_survey_settings(request, survey_id: str):
   try:
      user:User = request.user
      data = request.data
      survey = get_object_or_404(Surveys, id=survey_id)
      survey.am_i_d_owner(user)
      
      setting = get_object_or_404(SurveySettings, id=data['id'])
      
      settings = SurveySettingsSerializer(instance=setting, data=data, partial=True)
      
      if settings.is_valid():
         settings.save()
         return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
      else:
         return Response({'data':{},'message': str(settings.errors)}, status=HTTP_400_BAD_REQUEST)
      
   except Exception as e:
      return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@permission_classes([IsAuthenticated])
class LastUsedBlocksAPI(APIView):
   def post(self, request, survey_id: str):
      try:
         data = request.data
         user:User = request.user
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
         
         # The below code is using Django's `get_or_create` method to retrieve a `LastUsedBlocks`
         # object based on the specified criteria or create a new one if it doesn't exist. It is
         # looking for a `LastUsedBlocks` object with the specified `user.id`, `survey.id`, and
         # `block_type`. If such an object is found, it will be returned. If not found, a new
         # `LastUsedBlocks` object will be created with the provided `user.id`, `survey.id`, and
         # `block_type` values.
         LastUsedBlocks.objects.get_or_create(
            user__id=user.id,
            survey__id=survey.id,
            block_type=data['block_type'], defaults={
               'block_type': data['block_type'],
               'user': user,
               'survey': survey
            }
         )
         
         
         return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
         
      except Exception as e:
         print(e)
         return Response({'data':{},'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
      
   def get(self, request, survey_id: str):
      try:
         user:User = request.user
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
         
         last_used_blocks = LastUsedBlocks.objects.filter(
            Q(user__id=user.id) & Q(survey__id=survey_id)
         ).order_by('-created_at')[:10]
         
         data = LastUsedSerializerBlock(last_used_blocks, many=True)
         
         return Response({'data': data.data,'message': 'OK'}, status=HTTP_200_OK)
         
         
      except Exception as e:
         return Response({'data':{},'message': data.data}, status=HTTP_200_OK)

@permission_classes([IsAuthenticated])
class SurveyLogicApi(APIView):
   def post(self, request, survey_id: str):
        try:
            user = request.user
            data = request.data
            
            survey = get_object_or_404(Surveys, id=survey_id)
            survey.am_i_d_owner(user)
            
            with transaction.atomic():  # Use atomic transaction to ensure data integrity
                for logic_data in data.get('logics', []):
                    field = SurveyBlockType.objects.get(id=logic_data['field'])
                    fallBack = SurveyBlockType.objects.filter(id=logic_data['fallBack']).first() if logic_data['fallBack'] else None
                    
                    logic, created = SurveyLogic.objects.get_or_create(
                        survey=survey,
                        field=field,
                        defaults={
                          'operator':logic_data['operator'],
                          'value': logic_data['value'],
                          'endFunction': logic_data['endFunction'],
                          'fallBack': fallBack,
                          'endValue': logic_data['endValue'] or 0
                       }
                     )
                    
                    if not created:
                       logic.operator = logic_data['operator'] or logic.operator
                       logic.value = logic_data['value'] or logic.value
                       logic.endFunction = logic_data['endFunction'] or logic.endFunction
                       logic.fallBack = fallBack or logic.fallBack
                       logic.endValue = logic_data['endValue'] or logic.endValue
                       
                       logic.save()
            
            return Response({'data': {}, 'message': 'OK'}, status=HTTP_200_OK)
        
        except Exception as e:
            return Response({'data': {}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

   def delete(self, request, survey_id: str):
      try:
         user:User = request.user
         data = request.query_params
         
         print(data)
         
         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.am_i_d_owner(user)
         
         SurveyLogic.objects.get(survey__id=survey_id, id=data['id']).delete()
         
         
         return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
         
      except Exception as e:
         return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

# TODO:this is an un-finish function 
@permission_classes([IsAuthenticated])
class ConnectApps(APIView):
   def post(self, request, type):
      try:
         data = request.data
         
         apps = ['google_drive', 'excel']
         
         if type not in apps:
            return Response({'data':{},'message':'App type not available'}, status=HTTP_400_BAD_REQUEST)
         
         # ca = CA()
         
         if type == apps[0]:
            pass
            
         if type == apps[1]:
            pass
         
      except Exception as e:
         return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

   def get(self, request, type):
      try:
         
         data = request.query_params
         apps = ['google_drive', 'excel']
         
         credentials = None
         
         if type not in apps:
            return Response({'data':{},'message': str(e)}, status=HTTP_400_BAD_REQUEST)
         
         code = data['code']
         ca = ''
         
         if type == apps[0]:
           credentials = ca.exchange_code_for_access_token(code=code)
           
         
         print(credentials)
         
         return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
         
         
      except Exception as e:
         return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_survey_status(request, survey_id: str):
   try:
      user: User = request.user
      password = request.data['password']
      mode: str = request.data['mode']
      recipients = request.data.get('recipients', [])
      
      
      if mode not in ['DEVELOPMENT', 'PRODUCTION']:
         return Response({'data':{},'message':'Something went wrong'}, status=HTTP_400_BAD_REQUEST)
      
      if not user.check_password(password):
         return Response({'data':{},'message':'Incorrect password, please try again'}, status=HTTP_403_FORBIDDEN)
      
      survey = get_object_or_404(Surveys, id=survey_id)
      
      survey.am_i_d_owner(user)
      
      if survey.status == mode:
         return Response({'data':{},'message': f'This survey is already in {mode.capitalize()}'}, status=HTTP_409_CONFLICT)
      
      if survey.Status.DEVELOPMENT == survey.status:
         # Make survey that if end screen has a social media icon it should contain link
         # Calculate the time its going to take to complete the survey
         # Make survey that all the picture choices contain images
         
         # Getting the end_screen_ids
         end_screen_ids = SurveyBlockType.objects.filter(end_screen__isnull=False, survey__id=survey.id).values_list('end_screen__id', flat=True)


# Ensure that end_screen_ids is not empty
         if end_screen_ids:
    # Retrieve EndScreenSocialMedia objects using in_bulk()
            end_screens_social_media = EndScreenSocialMedia.objects.filter(end_screen__id__in=end_screen_ids).all()

    # Loop through the retrieved social_medias
            for social_media in end_screens_social_media:
        # Check if social_media_link is missing or invalid
               if 'http' not in social_media.social_media_link or 'www.' not in social_media.social_media_link:
                  return Response({'data': {}, 'message': f'{social_media.media_type.capitalize()} is missing a link, Please add it'}, status=HTTP_400_BAD_REQUEST)

               

         picture_ids = SurveyBlockType.objects.filter(picture_choice__isnull=False, survey__id=survey.id).values_list('picture_choice__id', flat=True)
         
         if len(picture_ids):
            
            pictures = PictureChoiceImages.objects.filter(picture__id__in=picture_ids)
            
            for picture in pictures:
               if 'http://' not in picture.url or 'https://' not in picture.url:
                  return Response({'data':{},'message':f"A picture choice is missing an image"}, status=HTTP_400_BAD_REQUEST)
         # If all the checks are passed then user can publish without any issue

         subject = f"New survey available for you by {survey.host.username}"
         body = ''
         
         if len(recipients): send_email(subject, body, recipients)

      # Perform a lot of checks before concluding to publish
      survey.status = mode
      
      
      survey.save()
      
      return Response({'data':{},'message':'OK'}, status=HTTP_200_OK)
   except Exception as e:
      return Response({'data':{},'message':str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)

class SurveyResponses(APIView):
   
   @permission_classes([IsAuthenticated])
   def get(self, request, survey_id: str):
      pass
   # Submit answers
   def post(self, request, survey_id: str):
      try:
         data = request.data
         user_id = data['userID']
         user_response = data['userResponses']
         

         
         survey = get_object_or_404(Surveys, id=survey_id)
         
         survey.check_close_date()
         survey.check_response_limit()
         
         user = get_object_or_404(SurveyParticipant, user_id=user_id, survey__id=survey.id)
         
         if user.survey_is_completed:
            return Response({'data':{'error':'is_completed'},'message':'Thank you for your participation, you have completed this survey'}, status=HTTP_409_CONFLICT)
            
         
         modify_user_responses = []
         
         
         for i in user_response:
            block = get_object_or_404(SurveyBlockType, id=i['block'])
            
            if block.is_required and not i['response']:
               return Response({'data':{},'message':"There are some required  questions that hasn't been answered."}, status=HTTP_400_BAD_REQUEST)
            
            data = {
               'response': i['response'],
               'block': block,
               'user': user
            }
            
            modify_user_responses.append(data)
           
         
         UserReponse.objects.bulk_create(modify_user_responses)
         
         # Mark this study as completed
         user.survey_is_completed = True
         user.save()

         return Response({'data':{},'message':''}, status=HTTP_200_OK)
         
         
      except Exception as e:
         return Response({'data':{}, 'message': str(e)}, status=HTTP_500_INTERNAL_SERVER_ERROR)