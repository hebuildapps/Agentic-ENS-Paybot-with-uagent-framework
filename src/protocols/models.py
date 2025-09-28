from typing import Optional, Dict, Any, List
from uagents import Model

class PaymentRequest(Model):
    prompt: str
    user_address: str
    chain_id: int = 11155111

class PaymentResponse(Model):
    success: bool
    message: str
    transaction: Optional[Dict[str, Any]] = None
    recipient_address: Optional[str] = None
    user_balance: Optional[float] = None
    error: Optional[str] = None
    metta_reasoning: Optional[Dict[str, Any]] = None
    knowledge_graph: Optional[List[str]] = None

class ChatMessage(Model):
    message: str
    user_id: Optional[str] = None

class ChatResponse(Model):
    message: str
    requires_wallet: bool = False
    transaction_data: Optional[Dict[str, Any]] = None

class AgentInfoQuery(Model):
    query_type: str = "capabilities"

class AgentInfoResponse(Model):
    name: str
    description: str
    capabilities: list
    examples: list