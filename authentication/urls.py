from django.urls import path
from .views import custom_login_view, logout_view

urlpatterns = [
    path('login/', custom_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
]
