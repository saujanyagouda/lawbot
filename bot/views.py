from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login as auth_login , logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json

User = get_user_model()

def home(request):
    return render(request, 'home.html',{"show_footer":True})
    
def about(request):
    return render(request, 'about.html',{"show_footer":True})

def contact(request):
    return render(request, 'contact.html',{"show_footer":True})

def login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        print(f'GOT EMAIL AND PASSWORD AS {email}:{password}')
        if not email or not password:
            messages.error(request, "Email and password are required.")
            return redirect("login")
        user = authenticate(request, email=email, password=password)  # Authenticate user
        if user is not None:
            auth_login(request, user)  # Log the user in
            return redirect('dashboard')
        else:
            messages.error(request, "Incorrect username or password. Please try again.")
            return redirect('login')
            


    return render(request,'login.html',{"show_footer":False})

def signup(request):
    if request.method == "POST":
        name = request.POST.get("fullname")
        email = request.POST.get("email")
        phone_number = request.POST.get("phone_number", None)  # Optional field
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm-password")
        #Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")  # Redirect to signup page
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect("signup")
        # Create user
        user = User.objects.create(
            username=name,  # Django's default username field
            email=email,
            phone_number=phone_number,
            password=make_password(password)  # Hash password before saving
        )
        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")  # Redirect to login page

    else:
      return render(request,'signup.html',{"show_footer":False})

@login_required
def dashboard(request):
    stats = {
        'total_clients': 100,
        'total_cases': 200,
        'important_cases': 10,
        'archived_cases': 5,
    }
    clients = [
      {
        'id': 1,
        'name': 'Will Cc Smith',
        'mobile': '0907937399',
        'cases': 1,
        'status': True
      }
    ]
    cases = [
      {
        'id': 1,
        'clientName': 'Will Cc Smith',
        'clientNo': '542344',
        'caseType': 'Murder',
        'court': 'RTC - Branch 4',
        'courtNo': '3123',
        'magistrate': 'Judge Marvin Tapuyo',
        'petitioner': 'Will Cc Smith',
        'respondent': 'Will Smith',
        'nextDate': '07-20-2021',
        'status': 'On-Trial',
        'isImportant': True
      }
    ]
    tasks = [
      {
        'id': 1,
        'taskName': 'Find Evidence',
        'relatedTo': {
          'name': 'Will Cc Smith',
          'caseNumber': '542344'
        },
        'startDate': '01-01-1970',
        'deadline': '01-01-1970',
        'members': ['D'],
        'status': 'In Progress',
        'priority': 'Urgent'
      }
    ]
    appointments = [
      {
        'id': 1,
        'clientName': 'Will Smith',
        'date': '07-17-2021',
        'time': '2:20 pm',
        'status': 'OPEN'
      }
    ]
    return render(request,'dashboard.html',{
        'clients': clients,
        'cases': cases,
        'tasks': tasks,
        'appointments': appointments,
        'stats': stats,
    })

@login_required
def task(request):
    return render(request,'task.html',{"show_footer":False})
def clients(request):
    return render(request,'clients.html',{"show_footer":False})

def setting(request):
    return render(request,'setting.html',{"show_footer":False})

def earnings(request):
    return render(request,'earnings.html',{"show_footer":False})

def teammember(request):
    return render(request,'teammember.html',{"show_footer":False})

def legalbot(request):
    return render(request,'legalbot.html',{"show_footer":False})

def appointments(request):
    return render(request,'appointments.html',{"show_footer":False})

def cases(request):
    return render(request,'cases.html',{"show_footer":False})
    
def logout(request):
    auth_logout(request)
    return redirect("/")
