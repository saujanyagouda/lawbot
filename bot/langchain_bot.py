import os
import json
from typing import Optional, Dict, List, Any
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic.v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
# from langchain_community.chat_models import AzureChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ZepChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
# Import duckduckgo-search for open source search
from duckduckgo_search import DDGS

# Import your Django models
from django.conf import settings
from .models import Client, Case, Task, Appointment, Invoice, CustomUser

llm = ChatOpenAI(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",  # Or use "meta-llama/Llama-2-7b-chat-hf"
    openai_api_key="",
    openai_api_base="https://api.together.xyz/v1",
)
#4691bd0a2080cfd38ae58e8645a07645faa98a9d9681dddba2b4490668d01e5b
# System prompt for the legal assistant
SYSTEM_PROMPT = """You are a legal assistant for a law firm in India. You help lawyers manage their practice by providing information about clients, cases, appointments, invoices, and tasks. You can also answer basic questions about Indian law.

When helping with practice management:
1. Always verify information before taking action
2. Be precise when dealing with dates, amounts, and legal information
3. Format responses clearly, using tables when displaying multiple records

When providing legal information:
1. Clarify that you're providing general information, not legal advice
2. Recommend consulting with a qualified attorney for specific legal matters
3. Cite relevant laws or regulations when possible
4. Always select the correct tool based on the user's request.

Remember that all information should be treated as confidential and you should follow all ethical guidelines for the legal profession in India.
"""

# Custom tool definitions

# Client Tools
class ClientCreateSchema(BaseModel):
    name: str = Field(..., description="Full name of the client")
    phone_number: str = Field(..., description="Client's phone number")
    email_address: str = Field(..., description="Client's email address")

@tool("client_create",return_direct=True)
def client_create(
    name: str,
    phone_number: str,
    email_address: str,
) -> str:
    """Create a new client in the system."""
    try:
        client = Client.objects.create(
            name=name,
            phone_number=phone_number,
            email_address=email_address
        )
        return f"Successfully created client: {client.name} with ID {client.id}"
    except Exception as e:
        return f"Error creating client: {str(e)}"

@tool("client_search",return_direct=True)
def client_search(query: str) -> str:
    """Search for clients by name, email, or phone number."""
    clients = Client.objects.filter(
        is_active=True
    ).filter(
        name__icontains=query
    ) | Client.objects.filter(
        email_address__icontains=query
    ) | Client.objects.filter(
        phone_number__icontains=query
    )
    
    if not clients:
        return "No clients found matching your query."
    
    results = "| ID | Name | Email | Phone |\n| --- | --- | --- | --- |\n"
    for client in clients:
        results += f"| {client.id} | {client.name} | {client.email_address} | {client.phone_number} |\n"
    
    return results

@tool("client_details",return_direct=True)
def client_details(client_id: int) -> str:
    """Get detailed information about a specific client."""
    try:
        client = Client.objects.get(id=client_id)
        
        # Get related data
        cases = Case.objects.filter(client=client)
        appointments = Appointment.objects.filter(client=client)
        invoices = Invoice.objects.filter(client=client)
        
        # Basic client info
        result = f"## Client: {client.name}\n"
        result += f"- Email: {client.email_address}\n"
        result += f"- Phone: {client.phone_number}\n"
        result += f"- Status: {'Active' if client.is_active else 'Inactive'}\n\n"
        
        # Cases
        result += f"## Cases ({cases.count()}):\n"
        if cases:
            result += "| Case Number | Type | Status | Next Hearing |\n"
            result += "| --- | --- | --- | --- |\n"
            for case in cases:
                result += f"| {case.case_number} | {case.case_type} | {case.status} | {case.next_hearing_date} |\n"
        else:
            result += "No cases found for this client.\n"
        
        # Appointments
        result += f"\n## Appointments ({appointments.count()}):\n"
        if appointments:
            result += "| Date | Time | Status | Topic |\n"
            result += "| --- | --- | --- | --- |\n"
            for appt in appointments:
                result += f"| {appt.date} | {appt.time} | {appt.status} | {appt.topic or 'N/A'} |\n"
        else:
            result += "No appointments scheduled for this client.\n"
        
        # Invoices
        result += f"\n## Invoices ({invoices.count()}):\n"
        if invoices:
            result += "| Invoice # | Amount | Paid | Due | Status |\n"
            result += "| --- | --- | --- | --- | --- |\n"
            for inv in invoices:
                result += f"| {inv.invoice_number} | {inv.total_amount} | {inv.paid_amount} | {inv.due_amount} | {inv.payment_status} |\n"
        else:
            result += "No invoices found for this client.\n"
        
        return result
        
    except Client.DoesNotExist:
        return f"Client with ID {client_id} not found."
    except Exception as e:
        return f"Error retrieving client details: {str(e)}"

# Case Tools
@tool("case_create",return_direct=True)
def case_create(
    client_id: int,
    case_number: str,
    case_type: str,
    court_name: str,
    court_number: str,
    magistrate_name: str,
    petitioner: str,
    respondent: str,
    next_hearing_date: str,
    status: str = "pending"
) -> str:
    """Create a new case for a client."""
    try:
        client = Client.objects.get(id=client_id)
        
        # Validate status
        valid_statuses = [choice[0] for choice in Case.STATUS_CHOICES]
        if status not in valid_statuses:
            return f"Invalid status. Choose from: {', '.join(valid_statuses)}"
        
        case = Case.objects.create(
            client=client,
            case_number=case_number,
            case_type=case_type,
            court_name=court_name,
            court_number=court_number,
            magistrate_name=magistrate_name,
            petitioner=petitioner,
            respondent=respondent,
            next_hearing_date=next_hearing_date,
            status=status
        )
        
        return f"Successfully created case {case.case_number} for client {client.name}"
    
    except Client.DoesNotExist:
        return f"Client with ID {client_id} not found."
    except Exception as e:
        return f"Error creating case: {str(e)}"

@tool("case_search",return_direct=True)
def case_search(query: str) -> str:
    """Search for cases by case number, type, court, or client name."""
    cases = Case.objects.filter(
        case_number__icontains=query
    ) | Case.objects.filter(
        case_type__icontains=query
    ) | Case.objects.filter(
        court_name__icontains=query
    ) | Case.objects.filter(
        client__name__icontains=query
    )
    
    if not cases:
        return "No cases found matching your query."
    
    results = "| Case Number | Type | Client | Status | Next Hearing |\n"
    results += "| --- | --- | --- | --- | --- |\n"
    
    for case in cases:
        results += f"| {case.case_number} | {case.case_type} | {case.client.name} | {case.status} | {case.next_hearing_date} |\n"
    
    return results

@tool("case_details",return_direct=True)
def case_details(case_number: str) -> str:
    """Get detailed information about a specific case."""
    try:
        case = Case.objects.get(case_number=case_number)
        
        result = f"## Case: {case.case_number}\n"
        result += f"- Type: {case.case_type}\n"
        result += f"- Status: {case.status}\n"
        result += f"- Client: {case.client.name}\n\n"
        
        result += "## Court Information\n"
        result += f"- Court: {case.court_name}\n"
        result += f"- Court Number: {case.court_number}\n"
        result += f"- Magistrate: {case.magistrate_name}\n\n"
        
        result += "## Case Parties\n"
        result += f"- Petitioner: {case.petitioner}\n"
        result += f"- Respondent: {case.respondent}\n\n"
        
        result += f"## Next Hearing: {case.next_hearing_date}\n"
        
        # Get related tasks
        tasks = Task.objects.filter(case_number=case.case_number)
        if tasks:
            result += "\n## Related Tasks\n"
            result += "| Task | Related To | Status | Priority | Deadline |\n"
            result += "| --- | --- | --- | --- | --- |\n"
            
            for task in tasks:
                result += f"| {task.task_name} | {task.related_to} | {task.status} | {task.priority} | {task.deadline} |\n"
        
        return result
    
    except Case.DoesNotExist:
        return f"Case with number {case_number} not found."
    except Exception as e:
        return f"Error retrieving case details: {str(e)}"

# Appointment Tools
@tool("appointment_create",return_direct=True)
def appointment_create(
    client_id: int,
    date: str,
    time: str,
    topic: str = None
) -> str:
    """Schedule a new appointment with a client."""
    try:
        client = Client.objects.get(id=client_id)
        
        appointment = Appointment.objects.create(
            client=client,
            date=date,
            time=time,
            topic=topic,
            status="OPEN"
        )
        
        return f"Successfully scheduled appointment with {client.name} on {date} at {time}"
    
    except Client.DoesNotExist:
        return f"Client with ID {client_id} not found."
    except Exception as e:
        return f"Error scheduling appointment: {str(e)}"

@tool("appointment_list",return_direct=True)
def appointment_list(date: str = None) -> str:
    """List appointments, optionally filtered by date."""
    query = Appointment.objects.all().order_by('date', 'time')
    
    if date:
        query = query.filter(date=date)
    
    if not query:
        return "No appointments found."
    
    results = "| Date | Time | Client | Status | Topic |\n"
    results += "| --- | --- | --- | --- | --- |\n"
    
    for appt in query:
        results += f"| {appt.date} | {appt.time} | {appt.client.name} | {appt.status} | {appt.topic or 'N/A'} |\n"
    
    return results

# Invoice Tools
@tool("invoice_create",return_direct=True)
def invoice_create(
    client_id: int,
    total_amount: float,
    service: str,
    payment_mode: str,
    due_date: str,
    paid_amount: float = 0.0
) -> str:
    """Create a new invoice for a client."""
    try:
        client = Client.objects.get(id=client_id)
        
        invoice = Invoice.objects.create(
            client=client,
            total_amount=total_amount,
            paid_amount=paid_amount,
            due_amount=total_amount - paid_amount,  # Will be recalculated in save()
            service=service,
            payment_mode=payment_mode,
            due_date=due_date
        )
        
        return f"Successfully created invoice {invoice.invoice_number} for client {client.name}"
    
    except Client.DoesNotExist:
        return f"Client with ID {client_id} not found."
    except Exception as e:
        return f"Error creating invoice: {str(e)}"

@tool("invoice_details",return_direct=True)
def invoice_details(invoice_number: str) -> str:
    """Get detailed information about a specific invoice."""
    try:
        invoice = Invoice.objects.get(invoice_number=invoice_number)
        
        result = f"## Invoice: {invoice.invoice_number}\n"
        result += f"- Client: {invoice.client.name}\n"
        result += f"- Service: {invoice.service}\n"
        result += f"- Total Amount: {invoice.total_amount}\n"
        result += f"- Paid Amount: {invoice.paid_amount}\n"
        result += f"- Due Amount: {invoice.due_amount}\n"
        result += f"- Payment Status: {invoice.payment_status}\n"
        result += f"- Payment Mode: {invoice.payment_mode}\n"
        result += f"- Due Date: {invoice.due_date}\n"
        result += f"- Created Date: {invoice.created_date}\n"
        
        return result
    
    except Invoice.DoesNotExist:
        return f"Invoice with number {invoice_number} not found."
    except Exception as e:
        return f"Error retrieving invoice details: {str(e)}"

# Task Tools
@tool("task_create",return_direct=True)
def task_create(
    task_name: str,
    related_to: str,
    case_number: str,
    start_date: str,
    deadline: str,
    priority: str = "Medium",
    status: str = "Pending"
) -> str:
    """Create a new task related to a case."""
    try:
        # Validate priority
        valid_priorities = [choice[0] for choice in Task.PRIORITY_CHOICES]
        if priority not in valid_priorities:
            return f"Invalid priority. Choose from: {', '.join(valid_priorities)}"
        
        # Validate status
        valid_statuses = [choice[0] for choice in Task.STATUS_CHOICES]
        if status not in valid_statuses:
            return f"Invalid status. Choose from: {', '.join(valid_statuses)}"
        
        task = Task.objects.create(
            task_name=task_name,
            related_to=related_to,
            case_number=case_number,
            start_date=start_date,
            deadline=deadline,
            priority=priority,
            status=status
        )
        
        return f"Successfully created task '{task.task_name}' for case {case_number}"
    
    except Exception as e:
        return f"Error creating task: {str(e)}"

@tool("task_list",return_direct=True)
def task_list(status: str = None) -> str:
    """List tasks, optionally filtered by status."""
    query = Task.objects.all().order_by('deadline')
    
    if status:
        query = query.filter(status=status)
    
    if not query:
        return "No tasks found."
    
    results = "| Task | Related To | Case | Status | Priority | Deadline |\n"
    results += "| --- | --- | --- | --- | --- | --- |\n"
    
    for task in query:
        results += f"| {task.task_name} | {task.related_to} | {task.case_number} | {task.status} | {task.priority} | {task.deadline} |\n"
    
    return results

# DuckDuckGo Search Tool for legal information - No API key required
@tool("duckduckgo_search",return_direct=True)
def duckduckgo_search(query: str) -> str:
    """Search for information using DuckDuckGo (no API key required)."""
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=5))
        
        if not results:
            return "No search results found for your query."
        
        formatted_results = "## Search Results\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"### {i}. {result.get('title', 'No Title')}\n"
            formatted_results += f"**Source**: {result.get('href', 'No URL')}\n"
            formatted_results += f"{result.get('body', 'No description available')}\n\n"
        
        return formatted_results
    
    except Exception as e:
        return f"Error performing search: {str(e)}"

# Define all tools
tools = [
    client_create,
    client_search,
    client_details,
    case_create,
    case_search,
    case_details,
    appointment_create,
    appointment_list,
    invoice_create,
    invoice_details,
    task_create,
    task_list,
    duckduckgo_search  # New DuckDuckGo search tool
]

# Create prompt template
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessage(content="{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools,allowed_tools=[tool.name for tool in tools], verbose=True)


class DjangoMessageHistory(BaseChatMessageHistory):
    """Message history backed by Django's database"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages = []  # Use a private attribute
        
        # Optionally, load messages from DB here
        # self._load_messages_from_db()
        
    def add_message(self, message):
        """Add a message to the history"""
        self._messages.append(message)
        # Save to DB here if needed
        
    def clear(self):
        """Clear message history"""
        self._messages = []
        # Clear from DB here if needed
        
    @property
    def messages(self):
        """Return the messages - this property is required"""
        return self._messages

def get_session_history(session_id: str):
    """Get or create a chat message history for a session"""
    # Return the message history directly
    return DjangoMessageHistory(session_id=session_id)

agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output",
)

def process_message(message: str, conversation_id: str, uploaded_file=None) -> str:
    """Process a message using the LangChain agent with Zep memory"""
    try:
        print(f"Received message: '{message}'")
        print(f"Conversation ID: '{conversation_id}'")
        # Handle file upload if present
        file_content = ""
        if uploaded_file:
            # Read file content depending on file type
            file_extension = uploaded_file.name.split('.')[-1].lower()
            
            if file_extension in ['txt', 'pdf', 'doc', 'docx']:
                # For text-based files, read the content
                file_content = f"\nThe user has uploaded a file named '{uploaded_file.name}'.\n"
                
                # For simplicity, we'll just read as text, but in a real app
                # you would use appropriate parsers
                try:
                    file_content += uploaded_file.read().decode('utf-8')
                except UnicodeDecodeError:
                    file_content += "This file contains binary content that couldn't be read as text."
                
                file_content += "\nPlease help the user with this document."
        
        # Combine the message with file content if any
        full_message = message
        if file_content:
            full_message = f"{message}\n\nFile Content: {file_content}"
        
        # Process with the agent
        response = agent_with_chat_history.invoke(
            {"input": full_message, "chat_history": []},
            config={"configurable": {"session_id": conversation_id}}
        )
        
        return response["output"]
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"I encountered an error processing your request: {str(e)}"