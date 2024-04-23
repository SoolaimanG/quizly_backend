from rest_framework.serializers import Serializer, ModelSerializer, SerializerMethodField

from .models import Surveys, UserReponse, SurveyBlockType, EndScreenSocialMedia, EndScreen, PhoneNumbers, PictureChoice, Date, Number, ShortText, LongText, DropDown, Rating, RedirectWithUrl, Website, WelcomeScreen, Choices, Email, YesNo, ChoicesOptions, DropDownOpions, PictureChoiceImages, SurveyDesign, SurveySettings, LastUsedBlocks, SurveyLogic

class SurveySettingsSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = SurveySettings

class PictureChoicesImageSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = PictureChoiceImages

class ChoicesOptionSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ChoicesOptions
        
class DropDownOptionSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = DropDownOpions

class EndScreenSocialMediaSerializer(ModelSerializer):
    class Meta:
        model = EndScreenSocialMedia
        fields = '__all__'
        
class EndScreenSerializer(ModelSerializer):
    class Meta:
        model = EndScreen
        fields = '__all__'

class SurveySerializer(ModelSerializer):
    response_count = SerializerMethodField(read_only=True)
    class Meta:
        
        exclude = ['host']
        model = Surveys
        
    def get_response_count(sef, obj:Surveys):
        return UserReponse.objects.filter(block__survey__id=obj.id).count()
    
class SurveyBlockSerializer(ModelSerializer):
    
    end_screen = SerializerMethodField()
    choices = SerializerMethodField()
    dropdown = SerializerMethodField()
    picture_choice = SerializerMethodField()
    
    class Meta:
        exclude = ['survey']
        model = SurveyBlockType
        depth = 1
        
    def get_end_screen(self, obj: SurveyBlockType):
        if obj.block_type == obj.BlockType.EndScreen:
            existing_data = EndScreenSerializer(obj.end_screen).data
            social_media = EndScreenSocialMedia.objects.filter(end_screen__id=obj.end_screen.id).all()
            print(social_media)
            social_media_data = EndScreenSocialMediaSerializer(social_media, many=True).data
            
            return {**existing_data, 'social_media': social_media_data}
        return None  # Return None if it's not an end screen block
    
    def get_choices(self, obj: SurveyBlockType):
        if obj.block_type == obj.BlockType.Choices:
            choices_options = ChoicesOptions.objects.filter(choices__id=obj.choices.id).all()
            
            existing_data = ChoicesSerializer(obj.choices).data
            data = ChoicesOptionSerializer(choices_options, many=True).data
            
            return {**existing_data, 'options': data}
        
    def get_dropdown(self, obj: SurveyBlockType):
        if obj.block_type == obj.BlockType.Dropdown:
            dropdown_options = DropDownOpions.objects.filter(drop_down__id=obj.dropdown.id).all()
            
            
            existing_data = DropDownSerializer(obj.dropdown).data
            data = DropDownOptionSerializer(dropdown_options, many=True).data
            
            return {**existing_data, 'options': data}
            
    def get_picture_choice(self, obj: SurveyBlockType):
        if obj.block_type == obj.BlockType.PictureChoice:
            picture_choices = PictureChoiceImages.objects.filter(picture__id=obj.picture_choice.id).all()
            
            
            existing_data = PictureChoiceSerializer(obj.picture_choice).data
            data = PictureChoicesImageSerializer(picture_choices, many=True).data
            
            return {**existing_data, 'images': data}
            
class SurveyDesignSerializer(ModelSerializer):
    class Meta:
        fields = '__all__' 
        model = SurveyDesign
            
# Blocks Serializer
class PhoneNumberSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = PhoneNumbers
        
class PictureChoiceSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = PictureChoice
        
class DateSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Date
        
class LongTextSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model =  LongText 
        
class ShortTextSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model =  ShortText 
        
class NumberSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Number
        
class NumberSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Number
        
class DropDownSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = DropDown
        
class RatingSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Rating
        
class RedirectWithUrlSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = RedirectWithUrl
        
class WebsiteSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Website
        
class WelcomeScreenSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = WelcomeScreen
        
class EmailSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Email
        
class YesNoSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = YesNo
        
class ChoicesSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Choices
        
class LastUsedSerializerBlock(ModelSerializer):
    class Meta:
        model = LastUsedBlocks
        exclude = ['user']

class SurveyLogicSerializer(ModelSerializer):
    class Meta:
        exclude = ['survey']
        model = SurveyLogic

