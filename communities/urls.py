from django.urls import path
from . import views

urlpatterns = [
 path('get-communities/<str:size>/', views.get_communities, name='get_communities'),
 path('am-i-a-member/', views.am_i_a_community_member, name='am_i_a_community_member'),
 path('join-or-leave-community/', views.join_or_leave_community, name='join_or_leave_community'),
 path("create-community/",views.create_community, name="create_community"),
 path('my-community/<str:id>/', views.MyCommunity.as_view(), name='my_community'),
 path('community-action/<str:post_id>/', views.community_action, name='community_action'),
 path('accept_or_reject/<str:id>/', views.reject_or_accept_request, name='accept_or_reject'),
 path('search-community/<str:id>/', views.search_community, name='search_community'),

]