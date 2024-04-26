from django.urls import path
from . import views


urlpatterns =[
    path('survey-workspace/', views.SurveysAPIVIEW.as_view()),
    path('generate-workspace-form/', views.generate_block_at_start),
    
    path('survey-blocks/<str:id>/', views.get_survey_details),
    path('block-actions/', views.SurveyBlocks.as_view()),
    path('change-block-to-preferred/<str:survey_id>/', views.change_block_to_preferred),
    path('edit-survey-design/<str:survey_id>/', views.edit_survey_designs),
    path('edit-survey-settings/<str:survey_id>/', views.edit_survey_settings),
    path('used-block/<str:survey_id>/', views.LastUsedBlocksAPI.as_view()),
    path('survey-logics/<str:survey_id>/', views.SurveyLogicApi.as_view()),
    path('survey-response/<str:survey_id>/', views.SurveyResponses.as_view()),
    path('publish-survey/<str:survey_id>/', views.toggle_survey_status)
]
