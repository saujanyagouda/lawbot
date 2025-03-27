import os
import json
from typing import Optional, Dict, List, Any, Union
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic.v1 import BaseModel, Field
from langchain.tools import BaseTool, StructuredTool, tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseLanguageModel
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from duckduckgo_search import DDGS

# Import your Django models
from django.conf import settings
from .models import Client, Case, Task, Appointment, Invoice, CustomUser

# LLM setup
llm = ChatOpenAI(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    openai_api_key="4691bd0a2080cfd38ae58e8645a07645faa98a9d9681dddba2b4490668d01e5b",
    openai_api_base="https://api.together.xyz/v1",
)

# More concise system prompt
SYSTEM_PROMPT = """You are a legal assistant for an Indian law firm. Help manage client information, cases, appointments, invoices, and tasks. Answer basic Indian law questions.

RESPOND IN JSON FORMAT:
1. For tool usage: {"type": "tool", "name": "tool_name", "params": {"param1": "value1"}}
2. For direct answers: {"type": "final_answer", "content": "Your response here"}

Tool selection guidelines:
- For client listings/search: Use 'client_search' with empty query for "list all clients"
- For appointment listings: Use 'appointment_list' for "list all appointments" 
- For legal questions about penalties, laws, or procedures: Use 'duckduckgo_search'
- For specific information: Use appropriate tools like 'case_search', 'client_details', etc.

For greetings or general questions, respond with a direct "final_answer" without using tools.
"""

# Client Tools
class ClientCreateSchema(BaseModel):
    name: str = Field(..., description="Full name of the client")
    phone_number: str = Field(..., description="Client's phone number")
    email_address: str = Field(..., description="Client's email address")

@tool("client_create")
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

@tool("client_search")
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

@tool("client_details")
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
@tool("case_create")
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

@tool("case_search")
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

@tool("case_details")
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
@tool("appointment_create")
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

@tool("appointment_list")
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
@tool("invoice_create")
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
            due_amount=total_amount - paid_amount,
            service=service,
            payment_mode=payment_mode,
            due_date=due_date
        )
        
        return f"Successfully created invoice {invoice.invoice_number} for client {client.name}"
    
    except Client.DoesNotExist:
        return f"Client with ID {client_id} not found."
    except Exception as e:
        return f"Error creating invoice: {str(e)}"

@tool("invoice_details")
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
@tool("task_create")
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

@tool("task_list")
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

# DuckDuckGo Search Tool
@tool("duckduckgo_search")
def duckduckgo_search(query: str) -> str:
    """Search for information using DuckDuckGo."""
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

# File handling tool
@tool("process_file")
def process_file(file_content: str, file_type: str) -> str:
    """Process uploaded file content."""
    try:
        if file_type.lower() == "text/plain":
            return f"File contents processed: {file_content[:100]}..."
        elif file_type.lower() in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return f"Processed {file_type} file. First 100 chars: {file_content[:100]}..."
        else:
            return f"Unsupported file type: {file_type}"
    except Exception as e:
        return f"Error processing file: {str(e)}"

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
    duckduckgo_search,
    process_file
]

# Create prompt template with JSON formatting
prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessage(content="{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent with robust parsing
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools,
    handle_parsing_errors=True,
    max_iterations=5,  # Allow more iterations for complex queries
    early_stopping_method="force",
    verbose=True,
    return_intermediate_steps=True  # This helps with debugging
)

# Chat history management
class MessageStore:
    """Simple in-memory message store"""
    def __init__(self):
        self.conversations = {}
        
    def get_messages(self, conversation_id: str):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        return self.conversations[conversation_id]
    
    def add_message(self, conversation_id: str, message):
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append(message)
        print(f"Added message to history ({conversation_id}): {message}")
    
    def clear_messages(self, conversation_id: str):
        self.conversations[conversation_id] = []
        print(f"Cleared message history for conversation: {conversation_id}")
        
    def print_history(self, conversation_id: str):
        if conversation_id not in self.conversations:
            print(f"No history for conversation: {conversation_id}")
            return
            
        print(f"=== CONVERSATION HISTORY ({conversation_id}) ===")
        for i, msg in enumerate(self.conversations[conversation_id]):
            content = msg.content if hasattr(msg, "content") else str(msg)
            msg_type = msg.__class__.__name__ if hasattr(msg, "__class__") else "Unknown"
            print(f"{i}: [{msg_type}] {content[:100]}{'...' if len(content) > 100 else ''}")
        print(f"=== END HISTORY ({conversation_id}) ===")

message_store = MessageStore()

class DjangoMessageHistory(BaseChatMessageHistory):
    """Message history backed by our message store"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        print(f"Initializing history for session: {session_id}")
        
    def add_message(self, message):
        """Add a message to the history"""
        message_store.add_message(self.session_id, message)
        
    def clear(self):
        """Clear message history"""
        message_store.clear_messages(self.session_id)
        
    @property
    def messages(self):
        """Return the messages"""
        msgs = message_store.get_messages(self.session_id)
        print(f"Retrieved {len(msgs)} messages for session: {self.session_id}")
        return msgs

def get_session_history(session_id: str):
    """Get or create a chat message history for a session"""
    print(f"Getting history instance for session: {session_id}")
    return DjangoMessageHistory(session_id=session_id)

agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output",
)

def process_message(message: str, conversation_id: str, uploaded_file=None) -> str:
    """
    Process a message from the user within a conversation.
    
    Args:
        message (str): The user's message text
        conversation_id (str): A unique identifier for this conversation
        uploaded_file (optional): A file object with read() method and content_type attribute
        
    Returns:
        str: The final response after processing and executing any necessary tools
    """
    try:
        print(f"Processing message: '{message}' for conversation: {conversation_id}")
        
        # Special case handling for direct questions that shouldn't go through the agent
        lower_message = message.lower().strip()

            
        # Function to execute a tool given its name and parameters
        def execute_tool(tool_name, params):
            print(f"Executing tool: {tool_name} with params: {params}")
            for tool in tools:
                if tool.name == tool_name:
                    # Convert params to the format expected by the tool
                    if isinstance(params, dict):
                        try:
                            # Use tool.invoke instead of direct call to avoid deprecation warning
                            result = tool.invoke(params)
                            print(f"Tool execution result type: {type(result)}")
                            return result
                        except Exception as e:
                            print(f"Error executing tool {tool_name}: {str(e)}")
                            return f"Error executing tool {tool_name}: {str(e)}"
                    else:
                        try:
                            # Use tool.invoke with dict for single parameter tools
                            if tool_name == "client_search":
                                result = tool.invoke({"query": params})
                            elif tool_name == "duckduckgo_search":
                                result = tool.invoke({"query": params})
                            elif tool_name == "appointment_list":
                                if params and params.lower() != "null":
                                    result = tool.invoke({"date": params})
                                else:
                                    result = tool.invoke({})
                            else:
                                # Fallback
                                result = tool.invoke({"query": params})
                            return result
                        except Exception as e:
                            print(f"Error executing tool {tool_name} with params {params}: {str(e)}")
                            return f"Error executing tool {tool_name}: {str(e)}"
            return f"Tool {tool_name} not found"
        
        # Direct command mapping
        tool_command_mapping = {
            "list all clients": ("client_search", {"query": ""}),
            "show all clients": ("client_search", {"query": ""}),
            "get all clients": ("client_search", {"query": ""}),
            "show clients": ("client_search", {"query": ""}),
            "list clients": ("client_search", {"query": ""}),
            
            "list all appointments": ("appointment_list", {}),
            "show all appointments": ("appointment_list", {}),
            "get all appointments": ("appointment_list", {}),
            "show appointments": ("appointment_list", {}),
            "get appointments": ("appointment_list", {}),
            "give me all appointments": ("appointment_list", {})
        }
        
        # Check for direct command match
        if lower_message in tool_command_mapping:
            tool_name, params = tool_command_mapping[lower_message]
            print(f"Direct tool match: {tool_name}")
            result = execute_tool(tool_name, params)
            return result
            
        # Prepare the input
        input_data = {"input": message}
        
        # Process uploaded file if present
        if uploaded_file:
            try:
                # Read file content
                file_content = uploaded_file.read()
                if isinstance(file_content, bytes):
                    file_content = file_content.decode('utf-8', errors='replace')
                
                # Call file processing tool directly
                file_result = process_file(file_content, uploaded_file.content_type)
                
                # Add file info to the message
                input_data["input"] = f"{message}\n\nUploaded file: {uploaded_file.name}\nFile analysis: {file_result}"
            except Exception as e:
                return f"Error processing uploaded file: {str(e)}"
        
        # Check for legal question pattern
        if any(keyword in lower_message for keyword in ["penalty", "fine", "punishment", "law", "legal", "court", "section"]):
            # Legal questions should use duckduckgo_search
            print(f"Legal question detected, using duckduckgo_search")
            result = execute_tool("duckduckgo_search", {"query": message})
            return result
            
        # Process the input through the agent for other queries
        print(f"Sending to agent: {message}")
        print(f"input_data: {input_data}")
        response = agent_with_chat_history.invoke(
            input_data,
            config={"configurable": {"session_id": conversation_id}}
        )
        
        # Extract the response
        if isinstance(response, dict) and "output" in response:
            raw_output = response["output"]
            print(f"Raw agent output: {raw_output[:100]}...")
        else:
            raw_output = str(response)
            print(f"Raw agent output (string): {raw_output[:100]}...")
        
        # Check if the response is already valid JSON
        try:
            json_data = json.loads(raw_output)
            print(f"Parsed JSON: {json_data}")
            # Check if this JSON indicates a tool call
            if json_data.get("type") == "tool":
                tool_name = json_data.get("name")
                params = json_data.get("params", {})
                
                print(f"Executing tool from JSON: {tool_name}")
                # Execute the tool
                result = execute_tool(tool_name, params)
                return result
            else:
                # It's already a final answer
                return json_data.get("content", raw_output)
        except json.JSONDecodeError:
            # The output might be formatted as JSON string but not proper JSON
            # Try to extract JSON with regex
            import re
            json_match = re.search(r'\{.*"type":\s*"[^"]*".*\}', raw_output, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    print(f"Found JSON with regex: {json_str}")
                    json_data = json.loads(json_str)
                    if json_data.get("type") == "tool":
                        tool_name = json_data.get("name")
                        params = json_data.get("params", {})
                        print(f"Executing tool from regex-JSON: {tool_name}")
                        result = execute_tool(tool_name, params)
                        return result
                    else:
                        return json_data.get("content", raw_output)
                except Exception as e:
                    print(f"Error parsing regex JSON: {str(e)}")
                    
            # Not JSON, check for ReAct format
            if "Action:" in raw_output and "Action Input:" in raw_output:
                # Try to extract tool name and parameters
                try:
                    # Extract the tool name
                    action_parts = raw_output.split("Action:")
                    tool_name = action_parts[1].split("\n")[0].strip()
                    print(f"Found tool in ReAct format: {tool_name}")
                    
                    # Extract parameters
                    if "Action Input:" in raw_output:
                        action_input_parts = raw_output.split("Action Input:")
                        action_input_text = ""
                        
                        if len(action_input_parts) > 1:
                            if "Observation:" in action_input_parts[1]:
                                action_input_text = action_input_parts[1].split("Observation:")[0].strip()
                            else:
                                action_input_text = action_input_parts[1].strip()
                    
                    # Parse action input
                    try:
                        # Try to parse as JSON
                        params = json.loads(action_input_text)
                    except:
                        # Special handling for different tools
                        if tool_name == "client_search":
                            params = {"query": action_input_text}
                        elif tool_name == "appointment_list":
                            if action_input_text and action_input_text.lower() != "null":
                                params = {"date": action_input_text}
                            else:
                                params = {}
                        elif tool_name == "duckduckgo_search":
                            params = {"query": action_input_text}
                        else:
                            # Default handling
                            params = {"query": action_input_text}
                    
                    # Execute the tool
                    print(f"Executing tool from ReAct: {tool_name}")
                    result = execute_tool(tool_name, params)
                    return result
                except Exception as e:
                    print(f"Error parsing ReAct format: {str(e)}")
                    # Fallback if parsing fails
                    return raw_output
            else:
                # It's a direct answer
                return raw_output
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        print(f"Error in process_message: {str(e)}\n{trace}")
        # Handle any unexpected errors
        return f"Error processing your request: {str(e)}"

# Direct LLM query without tools
def query_llm_directly(message: str) -> str:
    """Query the LLM directly without using tools."""
    try:
        response = llm.invoke(message)
        return json.dumps({
            "type": "final_answer",
            "content": response.content
        })
    except Exception as e:
        return json.dumps({
            "type": "final_answer",
            "content": f"Error querying LLM: {str(e)}"
        })