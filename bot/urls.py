from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/',views.about, name='about'),
    path('login/',views.login,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('signup/',views.signup,name='signup'),
    path('contact/',views.contact,name='contact'),
    path('task/',views.task,name='task'),
    path('setting/',views.setting,name='setting'),
    path('legalbot/',views.legalbot,name='legalbot'),
    path('clients/',views.clients,name='clients'),
    path('cases/',views.cases,name='cases'),
    path('appointments/',views.appointments,name='appointments'),
    path('teammember/',views.teammember,name='teammember'),
    path('earnings/',views.earnings,name='earnings'),
    path('forgat_password/',views.earnings,name='forgot-password'),
    path('logout/',views.logout,name='logout')
]
