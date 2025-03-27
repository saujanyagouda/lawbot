

import os
import logging
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.schema import Document
import numpy as np

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Set API key - Replace with your Google API key
GOOGLE_API_KEY = "AIzaSyC5tE6SBzeHCn3ECAGvboqMSJ-ZYu0Qbf4"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Vector database configuration
SIMILARITY_THRESHOLD = 0.60  # Threshold for considering a match
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# Sample legal FAQs - Static list instead of database
LEGAL_FAQS = [
    {
        "question": "What is the punishment for theft under Indian Penal Code?",
        "answer": "Under Section 379 of Indian Penal Code, theft is punishable with imprisonment up to 3 years, or fine, or both. The severity of punishment can vary based on the value of stolen property and circumstances.",
        "category": "Criminal",
        "tags": ["theft", "IPC", "punishment"],
        "legislation_ref": "IPC Section 379"
    },
    {
        "question": "How do I file for divorce in India?",
        "answer": "To file for divorce in India, you need to submit a petition in the family court having jurisdiction where you last resided with your spouse. You can file under various grounds like cruelty, desertion, adultery, etc. as per the Hindu Marriage Act (for Hindus), Special Marriage Act, or personal laws applicable to your religion. The process typically involves filing the petition, attending court hearings, and potentially going through mediation or counseling sessions.",
        "category": "Family",
        "tags": ["divorce", "procedure", "family law"],
        "legislation_ref": "Hindu Marriage Act, Special Marriage Act"
    },
    {
        "question": "What is the limitation period for filing a cheque bounce case?",
        "answer": "The limitation period for filing a cheque bounce case under Section 138 of the Negotiable Instruments Act is 30 days from the date of receipt of notice from the bank regarding the dishonor of the cheque. After receiving this notice, the payee must send a demand notice to the drawer within 30 days, demanding payment. If payment is not made within 15 days of receiving this demand notice, a complaint can be filed in court within 30 days after the expiry of these 15 days.",
        "category": "Commercial",
        "tags": ["cheque bounce", "138", "limitation"],
        "legislation_ref": "Negotiable Instruments Act Section 138"
    },
    {
        "question": "What is the process for registering a property in India?",
        "answer": "The property registration process in India involves: 1) Verifying property documents and ensuring clear title, 2) Obtaining an encumbrance certificate, 3) Drafting a sale deed, 4) Paying stamp duty (varies by state, typically 5-7% of property value), 5) Paying registration fee (typically 1% of value), 6) Getting the sale deed executed and registered at the Sub-Registrar's office where the property is located. Both buyer and seller must be present with witnesses during registration.",
        "category": "Property",
        "tags": ["property", "registration", "real estate"],
        "legislation_ref": "Registration Act, 1908; Transfer of Property Act, 1882"
    },
    {
        "question": "What is the process for filing an FIR in India?",
        "answer": "To file an FIR (First Information Report) in India: 1) Visit the police station with jurisdiction over the area where the crime occurred, 2) Provide a detailed written or verbal statement about the incident, 3) The officer must record your statement if it relates to a cognizable offense, 4) Review the FIR before signing it, 5) Collect a free copy of the FIR. If the police refuse to register your FIR, you can approach the Superintendent of Police or file a complaint with the magistrate under Section 156(3) of CrPC.",
        "category": "Criminal",
        "tags": ["FIR", "police", "criminal procedure"],
        "legislation_ref": "Criminal Procedure Code Sections 154, 156"
    },
    {
        "question": "What are the grounds for divorce in India?",
        "answer": "The grounds for divorce in India vary based on personal laws, but commonly include: 1) Cruelty (physical or mental), 2) Desertion for a continuous period (typically 2+ years), 3) Adultery, 4) Conversion to another religion, 5) Mental disorder/insanity, 6) Communicable disease like HIV/AIDS or venereal disease, 7) Presumption of death (missing for 7+ years), 8) No resumption of cohabitation after a decree of separation, 9) Mutual consent. For Hindus, these are specified in the Hindu Marriage Act; for others, respective personal laws or the Special Marriage Act apply.",
        "category": "Family",
        "tags": ["divorce", "grounds", "family law"],
        "legislation_ref": "Hindu Marriage Act, Special Marriage Act"
    },
    {
        "question": "What is the procedure for bail in India?",
        "answer": "The bail procedure in India involves: 1) Filing a bail application in the appropriate court (Magistrate/Sessions/High Court depending on offense severity), 2) Notice to the public prosecutor, 3) Hearing arguments from both sides, 4) Court's decision based on case facts, crime severity, and flight risk, 5) If granted, fulfilling bail conditions like providing surety bonds and surrendering passport if required. For bailable offenses, bail is a right; for non-bailable offenses, it's at the court's discretion as per CrPC Sections 436-439.",
        "category": "Criminal",
        "tags": ["bail", "criminal procedure", "arrest"],
        "legislation_ref": "CrPC Sections 436-439"
    },
    {
        "question": "What is the right age of marriage in India?",
        "answer": "In India, the legal minimum age for marriage is 21 years for males and 18 years for females as per the Prohibition of Child Marriage Act, 2006. Any marriage where either party is below the respective age limit is considered a child marriage and is voidable (not automatically void). However, the government has recently proposed raising the minimum age of marriage for females to 21 years to bring it at par with males, though this amendment is not yet in effect.",
        "category": "Family",
        "tags": ["marriage", "age", "minor"],
        "legislation_ref": "Prohibition of Child Marriage Act, 2006"
    },
    {
        "question": "What is the punishment for drunk driving in India?",
        "answer": "The punishment for drunk driving (driving under the influence of alcohol) in India under Section 185 of the Motor Vehicles Act includes: First offense - Imprisonment up to 6 months or fine up to ₹10,000 or both. Second or subsequent offense - Imprisonment up to 2 years or fine up to ₹15,000 or both. Additionally, the driver's license can be suspended or revoked, and the vehicle may be impounded. The 2019 amendment to the Motor Vehicles Act has significantly increased these penalties from their previous amounts.",
        "category": "Criminal",
        "tags": ["drunk driving", "DUI", "traffic"],
        "legislation_ref": "Motor Vehicles Act Section 185"
    },
    {
        "question": "What are the documents required for property registration in India?",
        "answer": "Documents required for property registration in India typically include: 1) Sale deed/conveyance deed, 2) Previous title deeds establishing ownership chain, 3) Encumbrance certificate (proving property is free from legal liabilities), 4) Property tax receipts, 5) Approved building plan/layout, 6) NOC from housing society (if applicable), 7) Identity proof of buyer and seller (Aadhaar/PAN/Passport), 8) Photographs of parties, 9) Index-II (property's ownership history), 10) Land use conversion certificate (if applicable), and 11) Building completion certificate (for new constructions). Requirements may vary by state.",
        "category": "Property",
        "tags": ["property", "registration", "documents"],
        "legislation_ref": "Registration Act, 1908"
    }
]

# Global variables for LangChain components
retriever = None
llm = None
vectorstore = None

def create_document_from_faq(faq):
    """Convert FAQ dict to Document object for FAISS."""
    content = f"Question: {faq['question']}\nAnswer: {faq['answer']}"
    metadata = {
        "category": faq["category"],
        "tags": faq["tags"],
        "legislation_ref": faq["legislation_ref"]
    }
    return Document(page_content=content, metadata=metadata)

def initialize_faiss():
    """Initialize in-memory FAISS index with legal FAQs."""
    global retriever, llm, vectorstore
    
    logging.info("Initializing in-memory FAISS index with legal knowledge...")
    
    # Convert FAQs to Documents
    documents = [create_document_from_faq(faq) for faq in LEGAL_FAQS]
    logging.info(f"Created {len(documents)} documents for vector store")
    
    # Create FAISS index
    vectorstore = FAISS.from_documents(documents, embeddings)
    logging.info("FAISS index created successfully")
    
    # Setup retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}  # Retrieve top 4 most similar documents
    )
    
    # Setup LLM
    llm = ChatGoogleGenerativeAI(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="gemini-2.0-pro-exp-02-05"  # Use latest available model
    )
    
    logging.info("LawBot components initialized successfully")
    return True

def add_to_faiss(question, answer, category, tags=None, legislation_ref=None):
    """Add a new FAQ to the in-memory FAISS index."""
    global vectorstore, retriever
    
    if vectorstore is None:
        initialize_faiss()
    
    new_faq = {
        "question": question,
        "answer": answer,
        "category": category,
        "tags": tags or [],
        "legislation_ref": legislation_ref or ""
    }
    
    # Add to in-memory list for future reference
    LEGAL_FAQS.append(new_faq)
    
    # Create document and add to vectorstore
    document = create_document_from_faq(new_faq)
    vectorstore.add_documents([document])
    
    # Update retriever to use the updated vectorstore
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    
    logging.info(f"Added new FAQ to FAISS: {question[:30]}...")
    return True

def handle_legal_query(query, preferred_language="English"):
    """
    Handle legal queries with RAG pattern (Retrieval Augmented Generation).
    
    Args:
        query: The user's legal question
        preferred_language: Language preference for response
        
    Returns:
        str: Response to the legal query
    """
    global retriever, llm
    
    # Initialize if not already done
    if retriever is None or llm is None:
        initialize_faiss()
    
    logging.info(f"Received legal query: '{query}'")
    
    # Step 1: Retrieve relevant documents from FAISS
    docs = retriever.invoke(query)
    
    if docs:
        logging.info(f"Retrieved {len(docs)} document(s) from legal knowledge base")
        
        # Log retrieved documents
        for i, doc in enumerate(docs):
            logging.info(f"Doc {i + 1}: {doc.page_content[:100]}...")
            if hasattr(doc, 'metadata') and doc.metadata:
                logging.info(f"  Categories: {doc.metadata.get('category', 'N/A')}")
                logging.info(f"  Legislation: {doc.metadata.get('legislation_ref', 'N/A')}")
            
        # Combine documents into context with metadata
        context_parts = []
        for doc in docs:
            context_part = doc.page_content
            if hasattr(doc, 'metadata') and doc.metadata:
                if doc.metadata.get('legislation_ref'):
                    context_part += f"\nRelevant legislation: {doc.metadata.get('legislation_ref')}"
            context_parts.append(context_part)
            
        context = "\n\n".join(context_parts)

        # Step 2: Generate response with context
        prompt = f'''
        You are an Indian Legal Assistant bot specializing in Indian law.
        Use the provided legal information to answer the user's query accurately and professionally.
        Format your response in clear, concise language that a non-lawyer can understand.
        Include relevant Indian legal statutes, case precedents, or procedures when helpful.
        If you're unsure or the question requires personalized legal advice that should come from a qualified lawyer, 
        inform the user that they should consult with a licensed attorney and explain why.

        <legal_context>
        {context}
        </legal_context>

        User's query: {query}
        
        Preferred response language: {preferred_language}
        
        Provide your response in {preferred_language}:
        '''
        
        try:
            response = llm.invoke(prompt)
            if response and response.content:
                logging.info(f"Generated legal response (first 100 chars): {response.content[:100]}...")
                return response.content
            else:
                logging.warning("Empty response from language model.")
                return "I apologize, but I'm having trouble formulating a response. Please consult with a qualified legal professional for advice on this matter."

        except Exception as e:
            logging.error(f"Error generating legal response: {e}")
            return "I apologize, but I encountered a technical issue while processing your legal query. Please try again or consult with a qualified legal professional."
    
    # If no relevant legal information found
    logging.warning("No relevant legal information found. Using general legal knowledge...")
    try:
        # Fallback to general legal knowledge in the LLM
        prompt = f'''
        You are an Indian Legal Assistant bot specializing in Indian law.
        You're answering a legal question but don't have specific information from your legal database.
        Using your general knowledge about Indian law, provide the most accurate response possible.
        Be clear about any limitations in your response and when the user should consult a qualified legal professional.
        Format your answer to be clear, concise, and helpful while being honest about what you know and don't know.
        
        If this appears to be a question requiring specific legal expertise or case-specific advice,
        politely inform the user to consult a licensed attorney.

        User's query: {query}
        
        Preferred response language: {preferred_language}
        
        Provide your response in {preferred_language}:
        '''
        
        response = llm.invoke(prompt)
        if response and response.content:
            logging.info(f"Generated fallback legal response: {response.content[:100]}...")
            return response.content
        else:
            logging.warning("Empty fallback response.")
            return "I'm sorry, but I don't have enough information to provide an accurate answer to your legal question. Please consult with a qualified legal professional for proper advice."
            
    except Exception as e:
        logging.error(f"Error in fallback legal response: {e}")
        return "I apologize, but I'm unable to provide legal information on this topic. Please consult with a qualified legal professional for assistance."

def answer_direct_question(question, preferred_language="English"):
    """Answer direct question without retrieval for simple queries."""
    global llm
    
    # Initialize if not already done
    if llm is None:
        initialize_faiss()
    
    prompt = f'''
    You are an Indian Legal Assistant bot.
    Answer the following general question about Indian law or legal procedures:
    
    Question: {question}
    
    Provide a clear, accurate response based on Indian legal knowledge in {preferred_language}:
    '''
    try:
        response = llm.invoke(prompt)
        if response and response.content:
            return response.content
        return "I'm unable to provide an answer to this question at the moment."
    except Exception as e:
        logging.error(f"Error in direct question answering: {e}")
        return "I encountered a technical issue while processing your question. Please try again."

# Initialization
initialize_faiss()

# Simple function to determine if query is about law or general conversation
def is_legal_query(query):
    """Determine if a query is about legal matters or just conversation."""
    legal_terms = [
        "law", "legal", "court", "judge", "lawyer", "attorney", "case", "sue", "lawsuit",
        "divorce", "marriage", "property", "crime", "criminal", "punishment", "police",
        "rights", "bail", "warrant", "section", "act", "ipc", "crpc", "fine", "penalty",
        "registration", "contract", "agreement", "petition", "file", "testament", "will",
        "inheritance", "custody", "alimony", "maintenance"
    ]
    
    query_lower = query.lower()
    
    # Check for legal terms
    for term in legal_terms:
        if term in query_lower:
            return True
    
    # Check for question about specific laws or sections
    if any(x in query_lower for x in ["section", "act", "ipc", "crpc", "code"]):
        return True
        
    # For short queries, assume it's conversational
    if len(query_lower.split()) < 4:
        return False
        
    return False  # Default to conversation for ambiguous queries

# Main handler function to route queries appropriately
def process_query(query, preferred_language="English"):
    """Process user query and route to appropriate handler."""
    if not query or len(query.strip()) == 0:
        return "Please ask a question about Indian law or legal procedures."
    
    # Check language preference in query
    if "in hindi" in query.lower():
        preferred_language = "Hindi"
        query = query.lower().replace("in hindi", "").strip()
    elif "in tamil" in query.lower():
        preferred_language = "Tamil"
        query = query.lower().replace("in tamil", "").strip()
        
    # Determine query type and route appropriately
    if is_legal_query(query):
        return handle_legal_query(query, preferred_language)
    else:
        return answer_direct_question(query, preferred_language)

if __name__ == "__main__":
    # Interactive testing loop
    print("LawBot - Indian Legal Assistant")
    print("Type 'exit' to quit")
    
    while True:
        query = input("\nAsk a legal question: ")
        if query.lower() == 'exit':
            break
            
        response = process_query(query)
        print("\nResponse:", response)