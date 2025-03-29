from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/',views.about, name='about'),
    path('login/',views.login,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('signup/',views.signup,name='signup'),
    path('contact/',views.contact,name='contact'),
    path('app/',views.app,name='app'),
    path('task/',views.task,name='task'),
    path('setting/',views.setting,name='setting'),
    path('legalbot/',views.legalbot,name='legalbot'),
    path('api/initialize_chat/', views.initialize_chat, name='initialize_chat'),
    path('api/chat_response/', views.chat_response, name='chat_response'),
    path('clients/',views.clients,name='clients'),
    path('cases/',views.cases,name='cases'),
    path('appointments/',views.appointments,name='appointments'),
    path('appointments/get/<int:appointment_id>/', views.get_appointment, name='get_appointment'),
    path('teammember/',views.teammember,name='teammember'),
    path('invoice/',views.invoices,name='invoice'),
    path('invoice/get/<int:invoice_id>/', views.get_invoice, name='get_invoice'),
    path('download_invoice/<int:invoice_id>/', views.download_invoice, name='download_invoice'),
    path('forgot_password/',views.invoices,name='forgot-password'),
    path('logout/',views.logout,name='logout')
]
