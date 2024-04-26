from django.db import models
from uuid import uuid4
from django.utils.translation import gettext as _
from base.models import User
from django.utils import timezone 

from django.db.models import Q


class EndScreenSocialMedia(models.Model):
    
    class SocialMediaType(models.TextChoices):
        INSTAGRAM = 'instagram',_('INSTAGRAM'),
        FACEBOOK = 'facebook',_('FACEBOOK'),
        WHATSAPP = 'whatsapp',_('WHATSAPP'),
        TWITTER = 'twitter',_('TWITTER'),
        EMAIL = 'email',_('EMAIL'),
        TIKTOK = 'tiktok',_('TIKTOK'),
    
    id = models.UUIDField(default=uuid4, primary_key=True)
    social_media_link = models.URLField()
    media_type = models.TextField(choices=SocialMediaType.choices, default=SocialMediaType.EMAIL, max_length=20)
    end_screen = models.ForeignKey('EndScreen',on_delete=models.CASCADE)
    
    def clean(self):
        check_social_media = EndScreenSocialMedia.objects.filter(
        end_screen__id=self.end_screen.id, media_type=self.media_type
        )

        if check_social_media.exists() and check_social_media.get().pk != self.pk:
            raise ValueError('A social media entry with this type already exists.')

    
    def save(self, *arg, **kwarg):
        self.clean()
        super().save(*arg, **kwarg)

class Surveys(models.Model):

    class Status(models.TextChoices):
        DEVELOPMENT = 'DEVELOPMENT', _('DEVELOPMENT')
        PRODUCTION = 'PRODUCTION', _('PRODUCTION')

    id = models.UUIDField(primary_key=True, default=uuid4)
    name = models.TextField(max_length=250)
    status = models.TextField(choices=Status.choices, default=Status.DEVELOPMENT, max_length=15)
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    
    show_time_to_complete = models.BooleanField(default=False)
    show_number_of_submissions = models.BooleanField(default=False)
    
    close_date = models.DateField(null=True, blank=True)
    response_limit = models.IntegerField(default=None, null=True, blank=True)

    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    
    def am_i_d_owner(self, user:User):
        if self.host.id != user.id: 
            raise ValueError('You are not authorized to access this action')
        
    def check_close_date(self):
        settings = SurveySettings.objects.get(survey__id=self.id)
        if self.close_date is not None and settings.close_date >= self.close_date:
            raise ValueError('The survey close date cannot be earlier than the global close date')
    
    def check_response_limit(self):
        if self.response_limit is not None:
            all_responses = SurveyParticipant.objects.filter(survey__id=self.id).count()
            if all_responses >= self.response_limit:
                raise ValueError('This survey has reached the maximum number of response set by the host therefore cannot allow any other submissions')
    
    def __str__(self):
        return self.name

class Background(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    background_color = models.CharField(max_length=50, null=True)
    background_image = models.URLField(null=True)
    survey_block = models.ForeignKey('SurveyBlockType', on_delete=models.CASCADE, null=True, blank=True)

class PhoneNumbers(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    check_number = models.BooleanField(default=False)
    format_number = models.BooleanField(default=True)
    placeholder = models.CharField(max_length=500, default='Placeholder')
    
class PictureChoice(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    label = models.TextField(max_length=1000, null=True, blank=True)
    super_size = models.BooleanField(default=False)
    multiple_selection = models.BooleanField(default=True)
    
class PictureChoiceImages(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    picture = models.ForeignKey(PictureChoice, on_delete=models.CASCADE, null=True, blank=True)
    url = models.URLField()
    alt_tag = models.CharField(max_length=500, null=True, blank=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    saturation = models.PositiveIntegerField(default=0)
    contrast = models.PositiveIntegerField(default=0)
    brightness = models.PositiveIntegerField(default=0)
    blur = models.PositiveIntegerField(default=0)
    x = models.PositiveIntegerField(default=1)
    y = models.PositiveIntegerField(default=1)
    hue = models.PositiveIntegerField(default=1)
    grayscale = models.PositiveIntegerField(default=0)
    pixelate = models.PositiveIntegerField(default=0)
    rotationIndex = models.PositiveIntegerField(default=0)

class Date(models.Model):
   class Seperator(models.TextChoices):
       DASH = '-',_('-')
       DOT = '.',_('.')
       SLASH = '/',_('/')

   class Format(models.TextChoices):
       YEARFIRST = 'yyyy-MM-dd',_('yyyy-MM-dd')
       DAYFIRST = 'dd-MM-yyyy',_('dd-MM-yyyy')
       MONTHFIRST = 'MM-yyyy-dd',_('MM-yyyy-dd')
       DEFAULT = 'PPP', _('PPP')

   

   id = models.UUIDField(default=uuid4, primary_key=True)
   date = models.DateField(null=True, blank=True)
   label = models.TextField(max_length=1000, null=True, blank=True)
   seperator = models.TextField(choices=Seperator.choices, default=Seperator.SLASH, max_length=30)
   format = models.TextField(choices=Format.choices, default=Format.DAYFIRST, max_length=30)
   class PhoneNumber(models.Model):
    phone_number = models.CharField(max_length=30, null=True, blank=True)
    domain = models.CharField(max_length=5, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    
class Number(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    min = models.PositiveIntegerField(null=True, blank=True)
    max = models.PositiveIntegerField(null=True, blank=True)
    
class ShortText(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    max_character = models.PositiveIntegerField(default=100)
    label = models.TextField(max_length=1000, null=True, blank=True)
    place_holder = models.CharField(max_length=500, default='PlaceHolder')

class LongText(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    max_character = models.PositiveIntegerField(default=100)
    label = models.TextField(max_length=1000, null=True, blank=True)
    place_holder = models.CharField(max_length=500, default='PlaceHolder')
    
class DropDown(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    label = models.TextField(max_length=1000, null=True, blank=True)
    alphabetically = models.BooleanField(default=False)
    multiple_selection = models.BooleanField(default=True)
    allow_search = models.BooleanField(default=False)
    
class DropDownOpions(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    drop_down = models.ForeignKey(DropDown, on_delete=models.CASCADE, null=True, blank=True)
    body = models.TextField(max_length=1000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Rating(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    ratings_length = models.PositiveIntegerField(default=5)
    label = models.TextField(max_length=1000, null=True, blank=True)
    
class Choices(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    multiple_selection = models.BooleanField(default=True)
    vertical_alignment = models.BooleanField(default=False)
    label = models.TextField(max_length=1000, null=True, blank=True)
    randomize = models.BooleanField(default=False)

class Email(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    check_email = models.BooleanField(default=False)
    label = models.TextField(max_length=1000, null=True, blank=True)
    
class YesNo(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    allow_reselect = models.BooleanField(default=True)
    
class Website(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    accept_url_with = models.TextField(null=True, blank=True)
    label = models.TextField(max_length=1000, null=True, blank=True)
    
class RedirectWithUrl(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    url = models.URLField()
    message = models.TextField(max_length=1000, null=True, blank=True, default="Redirect to url")
    custom_html = models.TextField(max_length=10000, null=True, blank=True)
    click_option = models.BooleanField(default=True)
    button_text = models.CharField(default="Click here if you are not redirected.", max_length=500)
    
class WelcomeScreen(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    message = models.CharField(max_length=500)
    label = models.TextField(max_length=2000, null=True)
    have_continue_button = models.BooleanField(default=True)
    button_text = models.CharField(max_length=50, null=True, default='Start Questionaire.')
    background_image = models.URLField(null=True)
    custom_html = models.TextField(max_length=20000, null=True)
    time_to_complete = models.PositiveIntegerField(null=True)
    
class EndScreen(models.Model):
    button_link = models.URLField()
    message = models.CharField(max_length=500, default='Thank your for completing this survey')
    button_text = models.TextField(max_length=50, null=True, default='Button')
    
class ChoicesOptions(models.Model):
    choices = models.ForeignKey(Choices, on_delete=models.CASCADE)
    option = models.CharField(max_length=1000)
    id = models.UUIDField(primary_key=True, default=uuid4)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SurveyParticipant(models.Model):
    user_id = models.UUIDField(default=uuid4, primary_key=True)
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE, null=True)
    survey_is_completed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Validation here!
    pass

class UserReponse(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    user = models.ForeignKey(SurveyParticipant, on_delete=models.CASCADE, null=True)
    response = models.JSONField(default=list)
    block = models.ForeignKey('SurveyBlockType', on_delete=models.CASCADE, null=True)
    # browser_type = models.CharField()

class SurveySettings(models.Model):
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE)
    show_progress_bar = models.BooleanField(default=True)
    show_question_number = models.BooleanField(default=True)
    free_form_navigation = models.BooleanField(default=True)
    
    # Access and Scheduling
    schedule_close_date = models.BooleanField(default=False)
    close_date = models.DateTimeField(null=True, blank=True)
    set_response_limit = models.BooleanField(default=False)
    response_limit = models.PositiveIntegerField(default=10000)
    set_close_message = models.BooleanField(default=False)
    close_message = models.TextField(null=True, blank=True)
    
    # Validate data here
    def clean(self):
        back_date = self.close_date < timezone.now() if self.close_date else None
        check_schedule_close_date = self.schedule_close_date and not self.close_date or back_date
        check_response_limit = self.set_response_limit
        check_close_message = self.set_close_message and not self.close_message
        
        message = 'This feature is currently unavailable' if check_response_limit else 'Set a valid date' if back_date else 'Please set a schedule date' if check_schedule_close_date else 'Please a close message.'
        
        if any([check_close_message, check_response_limit, check_schedule_close_date]):
            raise ValueError(message)
    
    def save(self, *arg, **kwarg):
        self.clean()
        super().save(*arg, **kwarg)
    
class SurveyDesign(models.Model):

    class Colors(models.TextChoices):
        BLUE = 'BLUE',_('BLUE')
        GREEN = 'GREEN',_('GREEN')
        YELLOW = 'YELLOW',_('YELLOW')
        WHITE='WHITE',_('WHITE')
        
    class BackgroundColors(models.TextChoices):
        BLUE = 'BLUE',_('BLUE')
        GREEN = 'GREEN',_('GREEN')
        YELLOW = 'YELLOW',_('YELLOW')
        WHITE = 'WHITE',_('WHITE')
        
    class Button(models.TextChoices):
        BLUE = 'BLUE',_('BLUE')
        GREEN = 'GREEN',_('GREEN')
        YELLOW = 'YELLOW',_('YELLOW')
        
    class FontSize(models.TextChoices):
        SMALL = 'SMALL',_('SMALL')
        MEDIUM = 'MEDIUM',_('MEDIUM')
        LARGE = 'LARGE',_('LARGE')
        
    class FontFamily(models.TextChoices):
        SYSTEM = 'SYSTEM',_('SYSTEM')
        ARIAL = 'ARIAL',_('ARIAL')
        FUTURA = 'FUTURA',_('FUTURA')
        HELVETIA = 'HELVETIA',_('HELVETIA')
        GARAMOND = 'GARAMOND',_('GARAMOND')
        JOSEFIN_SANS = 'JOSEFIN_SANS',_('JOSEFIN_SANS')
        TIMES_NEW_ROMAN = 'TIMES_NEW_ROMAN',_('TIMES_NEW_ROMAN')

    class BorderRadius(models.TextChoices):
        SMALL = 'SMALL',_('SMALL')
        MEDIUM = 'MEDIUM',_('MEDIUM')
        LARGE = 'LARGE',_('LARGE')
    
    class ButtonText(models.TextChoices):
        BLUE = 'BLUE',_('BLUE')
        GREEN = 'GREEN',_('GREEN')
        YELLOW = 'YELLOW',_('YELLOW')
        WHITE = 'WHITE',_('WHITE')

    class BackgroundPattern(models.TextChoices):
        PatternOne = 'pattern-uvskajs',_('pattern-uvskajs')
        PatternTwo = 'pattern-euukzq',_('pattern-euukzq')
        PatternThree = 'pattern-ahwmak',_('pattern-ahwmak')
        PatternFour = 'pattern-ydfyai',('pattern-ydfyai')
        PatternFive = 'pattern-arywav',_('pattern-arywav')
        PatternSix = 'pattern-arraaj',('pattern-arraaj')
        Non = 'Non',_('Non')
        

    id = models.UUIDField(default=uuid4, primary_key=True)
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE)
    color = models.TextField(choices=Colors.choices, default=Colors.GREEN, max_length=10)
    button = models.TextField(choices=Button.choices, default=Button.GREEN, max_length=10)
    font_size = models.TextField(choices=FontSize.choices, default=FontSize.MEDIUM, max_length=10)
    font_family = models.TextField(choices=FontFamily.choices, default=FontFamily.SYSTEM, max_length=50)
    border_radius = models.TextField(choices=BorderRadius.choices, default=BorderRadius.MEDIUM, max_length=10)
    button_text = models.TextField(choices=ButtonText.choices, default=ButtonText.WHITE, max_length=10)
    background_color = models.TextField(choices=BackgroundColors.choices, default=BackgroundColors.WHITE, max_length=10)
    background_pattern = models.TextField(choices=BackgroundPattern.choices, default=BackgroundPattern.Non, max_length=40)
    
class SurveyBlockType(models.Model):

    class BlockType(models.TextChoices):
        ContactInfo = "ConatctInfo", _('ContactInfo')
        Email = 'Email', _("Email")
        PhoneNumber = 'PhoneNumber', _('PhoneNumber')
        Website = "Website", _('Website')
        Choices = "Choices", _('Choices')
        Dropdown = "DropDown", _('DropDown')
        PictureChoice = "PictureChoice", _('PictureChoice')
        YesNo = "YesNo", _("YesNo")
        Rating = "Rating", _('Rating')
        LongText = "LongText", _("LongText")
        ShortText = "ShortText", _("ShortText")
        Time = "Time", _("Time")
        Date ="Date",_("Date")
        Number = "Number",_("Number")
        QuestionGroup = "QuestionGroup",('QuestionGroup')
        EndScreen= "EndScreen",_("EndScreen")
        RedirectToURL = "RedirectToURL", _("RedirectToURL")
        WelcomeScreen = "WelcomeScreen", _("WelcomeScreen")

    
    id = models.UUIDField(default=uuid4, primary_key=True)
    question = models.TextField(max_length=250, null=True)
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE, related_name='survey_blocks')
    block_type = models.TextField(choices=BlockType.choices, default=BlockType.ShortText)
    is_required = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    label = models.TextField(max_length=5000, null=True, blank=True)
    dropdown = models.ForeignKey(DropDown, on_delete=models.CASCADE, null=True, blank=True, related_name='dropdown_blocks')
    ratings = models.ForeignKey(Rating, on_delete=models.CASCADE, null=True, blank=True, related_name='rating_blocks')
    email = models.ForeignKey(Email, on_delete=models.CASCADE, null=True, blank=True, related_name='email_blocks')
    phone_number = models.ForeignKey(PhoneNumbers, on_delete=models.CASCADE, null=True, blank=True, related_name='phone_number_blocks')
    picture_choice = models.ForeignKey(PictureChoice, on_delete=models.CASCADE, null=True, blank=True, related_name='picture_choice_blocks')
    date = models.ForeignKey(Date, on_delete=models.CASCADE, null=True, blank=True, related_name='date_blocks')
    number = models.ForeignKey(Number, on_delete=models.CASCADE, null=True, blank=True, related_name='number_blocks')
    short_text = models.ForeignKey(ShortText, on_delete=models.CASCADE, null=True, blank=True, related_name='short_text_blocks')
    long_text = models.ForeignKey(LongText, on_delete=models.CASCADE, null=True, blank=True, related_name='long_text_blocks')
    choices = models.ForeignKey(Choices, on_delete=models.CASCADE, null=True, blank=True, related_name='choices_blocks')
    yes_no = models.ForeignKey(YesNo, on_delete=models.CASCADE, null=True, blank=True, related_name='yes_no_blocks')
    website = models.ForeignKey(Website, on_delete=models.CASCADE, null=True, blank=True, related_name='website_blocks')
    redirect_with_url = models.ForeignKey(RedirectWithUrl, on_delete=models.CASCADE, null=True, blank=True, related_name='redirect_with_url_blocks')
    welcome_screen = models.ForeignKey(WelcomeScreen, on_delete=models.CASCADE, null=True, blank=True, related_name='welcome_screen_blocks')
    end_screen = models.ForeignKey(EndScreen, on_delete=models.CASCADE, null=True, blank=True, related_name='end_screen_blocks')
    index = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.survey.name + ' ' + self.block_type
    
    def correct_all_index(self):
        all_blocks_gt_current_index = SurveyBlockType.objects.filter(
          Q(survey__id=self.survey.id) & Q(index__gt=self.index) 
        )
        
        for _ in all_blocks_gt_current_index:
            block = all_blocks_gt_current_index.first()
            block.index += 1
            block.save()
            
    def save(self, *arg, **kwarg):
        self.correct_all_index()
        super().save(*arg, **kwarg)

class LastUsedBlocks(models.Model):
    id = models.UUIDField(default=uuid4, primary_key=True)
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE)
    block_type = models.TextField(choices=SurveyBlockType.BlockType.choices, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    
    def __str__(self):
        return self.block_type

class SurveyLogic(models.Model):
    class Operator(models.TextChoices):
        eq = 'eq', _("eq")
        ne = 'ne', _('eq')
        gt = 'gt',_('gt')
        lt = 'lt',_('lt')
        includes = 'includes', _('includes')
        not_include = 'not_include',_('not_include')
    
    class EndFunction(models.TextChoices):
        goto = 'goto', _('goto')
        disable_btn = 'disable_btn', _('disable_btn')
    
    
    id=models.UUIDField(default=uuid4, primary_key=True)
    survey = models.ForeignKey(Surveys, on_delete=models.CASCADE)
    
    field = models.ForeignKey(SurveyBlockType, on_delete=models.CASCADE)
    operator = models.TextField(choices=Operator.choices, null=True, blank=True)
    value = models.CharField(max_length=200)
    endFunction = models.TextField(choices=EndFunction.choices, null=True, blank=True)
    endValue = models.PositiveSmallIntegerField(null=True, blank=True)
    fallBack = models.ForeignKey(SurveyBlockType, on_delete=models.CASCADE, null=True, blank=True, related_name='fallBack_modal')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['field', 'survey']

    
    def clean(self):
        try:
            if self.endFunction == self.EndFunction.disable_btn and not bool(int(self.endValue)):
                raise ValueError('Please add a timer for the button to be disabled (Seconds)')
            
            if self.endFunction == self.EndFunction.goto and not self.fallBack:
                raise ValueError('Please add a fall back block.')
            
        except Exception as e:
            raise e
    
    def save(self, *arg, **kwarg):
        
        self.clean()
        super().save(*arg, **kwarg)


    