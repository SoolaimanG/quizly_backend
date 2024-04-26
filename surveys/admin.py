from django.contrib import admin

from .models import Surveys, SurveyBlockType, SurveySettings, ShortText, LongText, Choices, Website, WelcomeScreen, Rating, RedirectWithUrl, Email, EndScreen, PhoneNumbers, PictureChoice, PictureChoiceImages, Number, YesNo, Date, ChoicesOptions, DropDown, EndScreenSocialMedia, SurveyDesign, LastUsedBlocks, SurveyLogic, SurveyParticipant


admin.site.register(Surveys)
admin.site.register(SurveyBlockType)
admin.site.register(SurveySettings)
admin.site.register(ShortText)
admin.site.register(LongText)
admin.site.register(Choices)
admin.site.register(Website)
admin.site.register(WelcomeScreen)
admin.site.register(Rating)
admin.site.register(RedirectWithUrl)
admin.site.register(Email)
admin.site.register(EndScreen)
admin.site.register(Number)
admin.site.register(PhoneNumbers)
admin.site.register(PictureChoice)
admin.site.register(PictureChoiceImages)
admin.site.register(YesNo)
admin.site.register(Date)
admin.site.register(ChoicesOptions)
admin.site.register(DropDown)
admin.site.register(EndScreenSocialMedia)
admin.site.register(SurveyDesign)
admin.site.register(LastUsedBlocks)
admin.site.register(SurveyLogic)
admin.site.register(SurveyParticipant)

# Register your models here.
