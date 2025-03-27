from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login as auth_login , logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from .models import Client, Task, Case, Appointment, Invoice
import random
import uuid
import json
from .langchain_bot import  handle_legal_query, answer_direct_question

User = get_user_model()

case_types = [
    "Criminal",
    "Civil",
    "Constitutional",
    "Administrative & Service",
    "Company & Business Law",
    "Taxation",
    "Arbitration & Mediation",
    "Environmental Law",
    "Intellectual Property"
]

courts = [
    "Supreme Court",
    "High Court",
    "District Court",
    "Sessions Court",
    "Family Court",
    "Consumer Court"
]

magistrates = [
    "Justice Ramesh Gupta",
    "Justice Priya Sharma",
    "Justice Anil Mehta",
    "Justice Kavita Rao",
    "Justice Vinay Patel",
    "Justice Pooja Deshmukh",
    "Justice Arjun Verma",
    "Justice Sanjay Nair"
]

# Generating dummy court data
dummy_courts = [
    {
        "court": "Supreme Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "Supreme Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "High Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "District Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "Sessions Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "Family Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    },
    {
        "court": "Consumer Court",
        "number": random.randint(50, 60),
        "magistrate": random.choice(magistrates)
    }
    
]


def is_simple_query(message):
    """
    Determine if a query is simple (greeting, small talk) or complex (legal question)
    """
    simple_patterns = [
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
        'how are you', 'what can you do', 'who are you', 'your name',
        'thanks', 'thank you'
    ]
    
    lower_message = message.lower()
    
    # Check if message is a simple greeting or small talk
    for pattern in simple_patterns:
        if pattern in lower_message:
            # Only match if the message is fairly short
            if len(lower_message.split()) < 8:
                return True
                
    return False

def email_send(subject,message,email):
    try:
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]

        send_mail(subject, message, from_email, recipient_list)
        return 'Email sent Successfully'
    except Exception as e:
        print(f'Got some error as: {e}')
        return 'Email sent Successfully'

def home(request):
    return render(request, 'home.html',{"show_footer":True})
    
def about(request):
    return render(request, 'about.html',{"show_footer":True})

def contact(request):
    if request.method=="POST":
        first_name = request.POST.get("first-name",None)
        last_name = request.POST.get("last-name",None)
        phone = request.POST.get("phone", " ")
        email = request.POST.get("email",None)
        subject = request.POST.get("subject"," ")
        message = request.POST.get("message"," ")
        if not first_name or not email:
            messages.error(request, "Name and Email is mandatory")
            return redirect("contact")
        new_message = f'Hello,\nYou have received a new contact form submission.\n\nName: {first_name} {last_name}\nPhone: {phone}\nEmail: {email}\nSubject: {subject}\nMessage: {message}'
        email_send('New Contact Form Submission',new_message,'goudasaujanya@gmail.com')

        new_message = '''Thank you for contacting us! We have received your message and our team will get back to you as soon as possible. We strive to respond within 24 hours, and we appreciate your patience.

        Thank you again for reaching out. We look forward to assisting you.

        Best regards,
        Team LawBot.'''
        email_send('Thank You for Reaching Out!',new_message,email)

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
        subject = "Welcome to Law Bot!"
        message = f"Hi {name},\n\nThank you for signing up for Law Bot. We’re excited to have you on board!\n\nBest Regards,\nThe Law Bot Team"
        from_email = settings.EMAIL_HOST_USER
        res = email_send(subject,message,email)
        print(res)
        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")  # Redirect to login page

    else:
      return render(request,'signup.html',{"show_footer":False})

@login_required
def dashboard(request):
    full_name = request.user.get_full_name()
    stats = {
        'total_clients': Client.objects.filter(user=request.user).count(),
        'total_cases': Case.objects.filter(user=request.user).count(),
        'appointments': Appointment.objects.filter(user=request.user).count(),
        'invoice': Invoice.objects.filter(user=request.user).count(),
    }
    today = timezone.now().date()
    
    clients = list(Client.objects.filter(user=request.user).order_by('-id')[:1])
    cases = list(Case.objects.filter(user=request.user).order_by('-id')[:1])
    tasks = list(Task.objects.filter(user=request.user).order_by('-id')[:1])
    appointments = list(Appointment.objects.filter(user=request.user, date=today).order_by('-id')[:1])
    return render(request,'dashboard.html',{
        'clients': clients,
        'cases': cases,
        'tasks': tasks,
        'appointments': appointments,
        'stats': stats,
        "username":full_name
    })

@login_required
def task(request):
    full_name = request.user.get_full_name()
    if request.method == "POST":
        print(request.POST)
        task_name = request.POST.get("taskName", "").strip()
        related_to = request.POST.get("relatedTo", "").strip()
        case_number = request.POST.get("caseNumber", "").strip()
        start_date = request.POST.get("startDate", "").strip()
        deadline = request.POST.get("deadline", "").strip()
        priority = request.POST.get("priority", "").strip()
        status = request.POST.get("status", "").strip()

        print(f"Task Name: {task_name}, Related To: {related_to}, Case Number: {case_number}")
        print(f"Start Date: {start_date}, Deadline: {deadline}, Priority: {priority}, Status: {status}")


        if not all([task_name, related_to, case_number, start_date, deadline, priority]):
            messages.error(request, "All fields are required.")
            return redirect("task")

        if Task.objects.filter(task_name=task_name, related_to=related_to, case_number=case_number, start_date=start_date).exists():
            messages.error(request, "A task with these details already exists.")
            return redirect("task")

        # Save the task
        Task.objects.create(
            task_name=task_name,
            related_to=related_to,
            case_number=case_number,
            start_date=start_date,
            deadline=deadline,
            priority=priority,
            status="Pending",
            user=request.user
        )
        print(f"✅ Task Saved:")
        messages.success(request, "Task added successfully!")
        return redirect("task")
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            task_id = data.get("taskId")
            print(f'GOT TASK ID AS {task_id}')
            if not task_id:
                return JsonResponse({"success": False, "error": "Task ID is required"}, status=400)
            task = get_object_or_404(Task, id=task_id)
            task.delete()

            return JsonResponse({"success": True})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, safe=False, status=400)
    elif request.method == "GET":
        db_tasks = Task.objects.filter(user=request.user)
        print(f"📊 Tasks Retrieved: {db_tasks}")  # Debugging
        for i in db_tasks:
            print(i.id)
        
        total_tasks= Task.objects.filter(user=request.user).count()          
        return render(request, "task.html", {"show_footer": False, "tasks": db_tasks,"username":full_name,"total_tasks":total_tasks})
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            print(f'GOT DATA AS:{data}')
            task = get_object_or_404(Task, id=data.get("taskId"))
            print('WE are here')
            task.task_name = data.get("taskName", task.task_name)
            task.case_number = data.get("caseNumber", task.case_number)
            task.related_to = data.get("relatedTo", task.related_to)
            task.start_date = data.get("startDate", task.start_date)
            task.deadline = data.get("deadline", task.deadline)
            task.priority = data.get("priority", task.priority)
            task.status = data.get("status", task.status)

            task.save()

            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT error as {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)

@login_required   
def clients(request):
    if request.method == "POST":
        print(request.POST)  # Debugging

        name = request.POST.get("clientName", "").strip()
        phone_number = request.POST.get("mobileNumber", "").strip()
        email = request.POST.get("email", "").strip()

        print(f'name is {name}')
        print(f'phone_number is {phone_number}')
        print(f'email is {email}')

        if not name or not phone_number or not email:
            messages.error(request, "All fields are required.")
            return redirect("clients")

        if Client.objects.filter(email_address=email).exists():
            messages.error(request, "A client with this email already exists.")
            return redirect("clients")

        if Client.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "A client with this phone number already exists.")
            return redirect("clients")

        # Save the client
        Client.objects.create(
            name=name,
            phone_number=phone_number,
            email_address=email,
            status=True,
            is_active=True,
            user=request.user
        )
        messages.success(request, "Client added successfully!")
        return redirect("clients")
    elif request.method =='DELETE':
        try:
            data =json.loads(request.body)
            name = data.get("name")
            email = data.get("email")
            phone_number = data.get("phone_number")
            client = Client.objects.filter(name=name, email_address=email, phone_number=phone_number).first()
            if client:
                client.delete()
                return JsonResponse({"success": True}, safe=False)  
                 
        except:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, safe=False, status=400) 

    elif request.method == 'GET':
        full_name = request.user.get_full_name()
        db_clients = Client.objects.filter(is_active=True,user=request.user)
        return render(request, "clients.html", {"show_footer": False,"clients":db_clients,"username":full_name})
    elif request.method =='PUT':
        name = request.PUT.get("clientName", "").strip()
        phone_number =request.PUT.get("mobileNumber","").strip()
        client = Client.objects.filter( phone_number=phone_number).first()
        return redirect("clients")



def setting(request):
    return render(request,'setting.html',{"show_footer":False})

@login_required
def invoices(request):
    if request.method == 'GET':
        full_name = request.user.get_full_name()
        # Get date range filters if provided
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        
        # Start with all invoices
        queryset = Invoice.objects.filter(user=request.user)
        
        # Apply date filters if provided
        if from_date:
            queryset = queryset.filter(created_date__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_date__date__lte=to_date)
            
        # Order by created date (newest first)
        invoices_list = queryset.order_by('-created_date')
        
        # Get all active clients for the dropdown
        clients = Client.objects.filter(is_active=True)
        
        context = {
            "show_footer": False,
            "invoices": invoices_list,
            "total_invoices": Invoice.objects.filter(user=request.user).count(),
            "clients": clients,
            "username":full_name
        }
        
        return render(request, 'invoices.html', context)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f'Got data as {data}')
            
            client = Client.objects.filter(id=data['client']).first()
            if not client:
                return JsonResponse({"success": False, "error": "Client is not available."}, status=400)
                
            # Create new invoice
            total_amount = float(data['totalAmount'])
            paid_amount = float(data['paidAmount'])
            due_date_naive = datetime.strptime(data['dueDate'], '%Y-%m-%d')
            due_date_aware = timezone.make_aware(due_date_naive, timezone.get_current_timezone())
            
            # Create new invoice
            Invoice.objects.create(
                client=client,
                total_amount=total_amount,
                paid_amount=paid_amount,
                service=data['service'],
                payment_mode=data['paymentMode'],
                due_date=due_date_aware,
                user=request.user
                # due_amount and payment_status will be calculated in save method
            )
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'Got error as {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            print(f'GOT DATA AS: {data}')
            
            invoice = get_object_or_404(Invoice, id=data.get("invoiceId"))
            print('Updating invoice...')
            
            # Update the invoice fields
            invoice.service = data.get("service", invoice.service)
            invoice.total_amount = float(data.get("totalAmount", invoice.total_amount))
            invoice.paid_amount = float(data.get("paidAmount", invoice.paid_amount))
            invoice.payment_mode = data.get("paymentMode", invoice.payment_mode)
            invoice.due_date = data.get("dueDate", invoice.due_date)
            
            # Save the invoice (due_amount and payment_status will be updated automatically)
            invoice.save()
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT ERROR AS: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            invoice_id = data.get("invoiceId")
            print(f'GOT invoice ID AS {invoice_id}')
            
            if not invoice_id:
                return JsonResponse({"success": False, "error": "Invoice ID is required"}, status=400)
                
            invoice = get_object_or_404(Invoice, id=invoice_id)
            invoice.delete()
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT ERROR AS: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    return render(request, 'invoices.html', {"show_footer": False})

# Additional endpoint to get invoice details for editing
def get_invoice(request, invoice_id):
    if request.method == 'GET':
        full_name = request.user.get_full_name()
        try:
            invoice = get_object_or_404(Invoice, id=invoice_id)
            
            # Format the data for frontend use
            invoice_data = {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "client_name": invoice.client.name,
                "total_amount": float(invoice.total_amount),
                "paid_amount": float(invoice.paid_amount),
                "due_amount": float(invoice.due_amount),
                "service": invoice.service,
                "payment_mode": invoice.payment_mode,
                "payment_status": invoice.payment_status,
                "due_date": invoice.due_date.strftime('%Y-%m-%d')
            }
            
            return JsonResponse({"success": True, "invoice": invoice_data})
        except Exception as e:
            print(f'Error fetching invoice: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)

# Function to download invoice PDF
def download_invoice(request, invoice_id):
    # For now, we're just serving a static PDF file
    # Later this can be replaced with dynamic PDF generation
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        
        # Path to a static invoice.pdf file
        # In a real application, you would generate this dynamically
        # file_path = os.path.join(settings.MEDIA_ROOT, 'invoices', 'invoice.pdf')
        
        # For now, as a placeholder, return a simple text response
        response = HttpResponse(f"Invoice #{invoice.invoice_number} for {invoice.client.name}",
                                content_type="text/plain")
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.txt"'
        return response
        
        # Uncomment when you have a real PDF file
        # if os.path.exists(file_path):
        #     return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
        # else:
        #     return HttpResponse("Invoice PDF not found", status=404)
    except Exception as e:
        print(f'Error downloading invoice: {e}')
        return HttpResponse(f"Error: {str(e)}", status=500)

def teammember(request):
    return render(request,'teammember.html',{"show_footer":False})

def legalbot(request):
    """Render the chatbot interface"""
    return render(request, 'legalbot.html', {"show_footer": False})

@require_POST
def initialize_chat(request):
    """Initialize a new chat session with a unique conversation ID"""
    conversation_id = str(uuid.uuid4())
    return JsonResponse({"conversation_id": conversation_id})

@require_POST
def chat_response(request):
    """Process the chat message and return a response"""
    user_message = request.POST.get('message', 'What is your name')
    conversation_id = request.POST.get('conversation_id', '')
    language = 'English'
    
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        
    if not user_message:
        return JsonResponse({
            'response': "I didn't receive any message. How can I assist you with your legal query?",
            'conversation_id': conversation_id
        })

    
    if is_simple_query(user_message):
        # For simple questions, use direct answering
        bot_response = answer_direct_question(user_message)
    else:
        # For complex legal queries, use the RAG system
        bot_response = handle_legal_query(user_message, language)
        
            
    # # Handle file upload if present
    # uploaded_file = None
    # if 'file' in request.FILES:
    #     uploaded_file = request.FILES['file']
    
    # Process the message using LangChain
    # response = process_message(bot_response, conversation_id,uploaded_file )
    
    return JsonResponse({"response": bot_response})

@login_required
def appointments(request):
    if request.method == 'GET':
        full_name = request.user.get_full_name()
        # Get date range filters if provided
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        
        # Start with all appointments
        queryset = Appointment.objects.filter(user=request.user)
        
        # Apply date filters if provided
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
            
        # Order by date and time
        appointments_list = queryset.order_by('date', 'time')
        
        # Get all active clients for the dropdown
        clients = Client.objects.filter(is_active=True)
        
        context = {
            "show_footer": False,
            "appointments": appointments_list,
            "total_appointments": Appointment.objects.count(),
            "clients": clients,
            "username":full_name
        }
        
        return render(request, 'appointments.html', context)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f'Got data as {data}')
            
            client = Client.objects.filter(id=data['client']).first()
            if not client:
                return JsonResponse({"success": False, "error": "Client is not available."}, status=400)
                
            # Create new appointment
            Appointment.objects.create(
                client=client,
                topic=data.get('topic', ''),
                date=data['date'],
                time=data['time'],
                status=data['status'],
                user=request.user
            )
            new_message = f' Topic: {data["topic"]}\n Date: {data["date"]}\n Time: {data["time"]}\n status: {data["status"]}'
            email_send('You have a new Appointment Scheduled',new_message,client.email_address)
            email_send('You have a new Appointment Scheduled',new_message,request.user.email)
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'Got error as {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            print(f'GOT DATA AS: {data}')
            
            appointment = get_object_or_404(Appointment, id=data.get("appointmentId"))
            print('Updating appointment...')
            
            # Update only the fields that can be edited
            appointment.date = data.get("date", appointment.date)
            appointment.time = data.get("time", appointment.time)
            appointment.status = data.get("status", appointment.status)
            
            appointment.save()
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT ERROR AS: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            appointment_id = data.get("appointmentId")
            print(f'GOT appointment ID AS {appointment_id}')
            
            if not appointment_id:
                return JsonResponse({"success": False, "error": "Appointment ID is required"}, status=400)
                
            appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment.delete()
            
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT ERROR AS: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    return render(request, 'appointments.html', {"show_footer": False})

# Additional endpoint to get appointment details for editing
def get_appointment(request, appointment_id):
    if request.method == 'GET':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            
            # Format the data for frontend use
            appointment_data = {
                "id": appointment.id,
                "client_name": appointment.client.name,
                "topic": appointment.topic,
                "date": appointment.date.strftime('%Y-%m-%d'),
                "time": appointment.time.strftime('%H:%M'),
                "status": appointment.status
            }
            
            return JsonResponse({"success": True, "appointment": appointment_data})
        except Exception as e:
            print(f'Error fetching appointment: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)

@login_required
def cases(request):
    if request.method == 'GET':
        full_name = request.user.get_full_name()
        db_clients = Client.objects.filter(is_active=True,user=request.user)
        db_cases = Case.objects.all() #TODO add isactive
        return render(request,'cases.html',{"show_footer":False,
        'clients':db_clients,
        'case_type':case_types,
        'courts':dummy_courts,
        'db_cases':db_cases,
        "username":full_name})
    elif request.method == 'POST':
        try:
            data =json.loads(request.body)
            print(f'Got data as {data}')
            if Case.objects.filter(case_number=data['CaseNumber']).exists():
                return JsonResponse({"success": False, "error": f"A case with {data['CaseNumber']} Number already exists."}, safe=False, status=400) 
    
            client = Client.objects.filter(id=data['ClientId']).first()
            if not client:
                return JsonResponse({"success": False, "error": f"Client is not available."}, safe=False, status=400) 
            Case.objects.create(
                client = client,
                case_number = data['CaseNumber'],
                case_type = data['caseType'],
                court_name = data['courtDropdown'],
                court_number = data['courtNoDropdown'],
                magistrate_name = 'Rajesh',
                petitioner = data['Petitioner'],
                respondent = data['Respondent'],
                next_hearing_date = data['Date'],
                status = data['Status'],
                user=request.user
            )
            return JsonResponse({"success": True})
        except Exception as e:
            print(f'Got error as {e}')
            return JsonResponse({"success": False, "error": "Invalid JSON"}, safe=False, status=400) 
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            print(f'GOT DATA AS: {data}')

            case = get_object_or_404(Case, id=data.get("caseId"))
            print('Updating case...')

            case.client_id = data.get("clientId", case.client_id)
            case.case_number = data.get("caseNumber", case.case_number)
            case.case_type = data.get("caseType", case.case_type)
            case.court_name = data.get("court", case.court_name)
            case.court_number = data.get("courtNo", case.court_number)
            case.petitioner = data.get("petitioner", case.petitioner)
            case.respondent = data.get("respondent", case.respondent)
            case.next_hearing_date = data.get("nextDate", case.next_hearing_date)
            case.status = data.get("status", case.status)

            case.save()

            return JsonResponse({"success": True})
        except Exception as e:
            print(f'GOT ERROR AS: {e}')
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({"success": False, "error": "Invalid request method"}, status=400)

        
    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            case_id = data.get("caseId")
            print(f'GOT case ID AS {case_id}')
            if not case_id:
                return JsonResponse({"success": False, "error": "Case ID is required"}, status=400)
            task = get_object_or_404(Case, id=case_id)
            task.delete()
            return JsonResponse({"success": True})
        except:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, safe=False, status=400) 
    return render(request,'cases.html',{"show_footer":False})
    
def logout(request):
    auth_logout(request)
    return redirect("/")
