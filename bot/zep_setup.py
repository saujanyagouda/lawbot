# zep_setup.py
import os
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ZepMemory:
    """
    Helper class for managing Zep memory server setup and connections.
    """
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
        }
        
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def health_check(self) -> bool:
        """
        Check if the Zep server is running and healthy.
        """
        try:
            response = requests.get(f"{self.api_url}/healthz", headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zep health check failed: {str(e)}")
            return False

    def create_collection(self, collection_name: str) -> bool:
        """
        Create a collection in Zep for storing memory.
        """
        try:
            payload = {
                "name": collection_name,
                "embedding_dimensions": 1536,  # For OpenAI embeddings
                "is_auto_embedded": True
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/collection",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Collection {collection_name} created successfully")
                return True
            elif response.status_code == 409:
                # Collection already exists
                logger.info(f"Collection {collection_name} already exists")
                return True
            else:
                logger.error(f"Failed to create collection: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating Zep collection: {str(e)}")
            return False

    def delete_memory(self, session_id: str) -> bool:
        """
        Delete a specific memory session.
        """
        try:
            response = requests.delete(
                f"{self.api_url}/api/v1/sessions/{session_id}",
                headers=self.headers
            )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting memory session: {str(e)}")
            return False

# Initialize memory system
def initialize_zep_memory():
    zep_url = "https://api.getzep.com"
    zep_api_key = "z_1dWlkIjoiYjcwZjY3YTMtNzY2Zi00OTUzLTk0NGEtNWEwMTYwYjRjYzVmIn0.apxm-fcsqZtMd-B55Fy0Pr8INeinf8x4I7AG-SapS4NMPVSvpXJRzvlywyrpCUEHN7FBKtmyQb3WcghYSUTWwg"
    
    zep = ZepMemory(api_url=zep_url, api_key=zep_api_key)
    
    # Check if Zep is running
    if not zep.health_check():
        logger.warning("Zep memory server is not available. "
                     "Chat history persistence will not work.")
        return False
    
    # Create collections for legal assistant
    collection_created = zep.create_collection("legal_assistant")
    
    if not collection_created:
        logger.warning("Failed to create Zep collection. "
                     "Chat history persistence may not work properly.")
        return False
    
    logger.info("Zep memory system initialized successfully")
    return True