import asyncio
import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from web3 import Web3
from ens import ENS
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading

load_dotenv()

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

agent = Agent(
    name="ens-pay-agent",
    port=8000,
    seed="ens-payment-agent-secret-seed-phrase",
    endpoint=["http://127.0.0.1:8000/submit"],
)

fund_agent_if_low(agent.wallet.address())

# Chain Configuration
CHAIN_CONFIG = {
    1: {
        "name": "Ethereum",
        "rpc": "https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY",
        "usdc": "0xA0b86a33E6441d7aE36C7c4AF2ABfC92d11f8b99"
    },
    137: {
        "name": "Polygon",
        "rpc": "https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY", 
        "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    },
    11155111: {
        "name": "Sepolia",
        "rpc": os.getenv("RPC_URL"),
        "usdc": os.getenv("USDC_CONTRACT_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    }
}

# MeTTa Knowledge Graph Implementation
class MeTTaKnowledgeGraph:
    def __init__(self):
        # Knowledge base as MeTTa facts and rules
        self.facts = []
        self.rules = []
        self.ens_cache = {}
        self.balance_cache = {}
        self.user_history = {}
        
        # Initialize with basic rules
        self.initialize_rules()
        
    def initialize_rules(self):
        """Add foundational MeTTa rules"""
        basic_rules = [
            "(= (valid-ens ?name) (ends-with ?name \".eth\"))",
            "(= (can-pay ?user ?amount) (>= (balance ?user) ?amount))",
            "(= (payment-safe ?user ?amount ?ens) (and (can-pay ?user ?amount) (valid-ens ?ens)))",
            "(= (large-payment ?amount) (> ?amount 1000))",
            "(= (suspicious-pattern ?user ?amount) (and (large-payment ?amount) (new-user ?user)))",
            "(= (new-user ?user) (< (user-age-days ?user) 1))"
        ]
        
        for rule in basic_rules:
            self.add_rule(rule)
        
    def add_fact(self, fact: str):
        """Add MeTTa fact to knowledge base"""
        if fact not in self.facts:
            self.facts.append(fact)
            
    def add_rule(self, rule: str):
        """Add MeTTa rule to knowledge base"""
        if rule not in self.rules:
            self.rules.append(rule)
        
    def query(self, query: str) -> List[str]:
        """Query the knowledge graph using MeTTa reasoning"""
        results = []
        
        try:
            # Parse different query types
            if "can-pay" in query:
                results = self._query_can_pay(query)
            elif "resolve-ens" in query:
                results = self._query_resolve_ens(query)
            elif "payment-safe" in query:
                results = self._query_payment_safe(query)
            elif "suspicious-pattern" in query:
                results = self._query_suspicious_pattern(query)
            else:
                results = [f"(unknown-query {query})"]
                
        except Exception as e:
            results = [f"(query-error {str(e)})"]
            
        return results
    
    def _query_can_pay(self, query: str) -> List[str]:
        """Process can-pay queries"""
        # Extract user and amount from query: (query (can-pay user123 5))
        parts = query.replace('(', ' ').replace(')', ' ').split()
        if len(parts) >= 4:
            user = parts[2]
            amount = float(parts[3])
            
            user_balance = self.get_cached_balance(user)
            
            if user_balance >= amount:
                result = f"(can-pay {user} {amount})"
                self.add_fact(result)
                return [result]
            else:
                result = f"(insufficient-balance {user} {amount} {user_balance})"
                self.add_fact(result)
                return [result]
        return ["(invalid-query-format)"]
    
    def _query_resolve_ens(self, query: str) -> List[str]:
        """Process ENS resolution queries"""
        parts = query.replace('(', ' ').replace(')', ' ').split()
        if len(parts) >= 3:
            ens_name = parts[2]
            address = self.get_cached_ens(ens_name)
            if address:
                result = f"(ens-address {ens_name} {address})"
                self.add_fact(result)
                return [result]
            else:
                return [f"(ens-unknown {ens_name})"]
        return ["(invalid-query-format)"]
    
    def _query_payment_safe(self, query: str) -> List[str]:
        """Process payment safety queries"""
        parts = query.replace('(', ' ').replace(')', ' ').split()
        if len(parts) >= 5:
            user = parts[2]
            amount = float(parts[3])
            ens_name = parts[4]
            
            # Check all safety conditions
            can_pay = self.get_cached_balance(user) >= amount
            valid_ens = ens_name.endswith('.eth')
            
            if can_pay and valid_ens:
                result = f"(payment-safe {user} {amount} {ens_name})"
                self.add_fact(result)
                return [result]
            else:
                issues = []
                if not can_pay:
                    issues.append("insufficient-balance")
                if not valid_ens:
                    issues.append("invalid-ens")
                result = f"(payment-unsafe {user} {amount} {ens_name} {' '.join(issues)})"
                self.add_fact(result)
                return [result]
        return ["(invalid-query-format)"]
    
    def _query_suspicious_pattern(self, query: str) -> List[str]:
        """Process suspicious pattern detection"""
        parts = query.replace('(', ' ').replace(')', ' ').split()
        if len(parts) >= 4:
            user = parts[2]
            amount = float(parts[3])
            
            # Check for suspicious patterns
            is_large = amount > 1000
            is_new_user = self.user_history.get(user, {}).get('age_days', 0) < 1
            
            if is_large and is_new_user:
                result = f"(suspicious-pattern {user} {amount} large-payment new-user)"
                self.add_fact(result)
                return [result]
            else:
                result = f"(normal-pattern {user} {amount})"
                self.add_fact(result)
                return [result]
        return ["(invalid-query-format)"]
    
    def get_cached_balance(self, user: str) -> float:
        """Get cached balance or return 0"""
        return self.balance_cache.get(user, 0.0)
    
    def get_cached_ens(self, ens_name: str) -> str:
        """Get cached ENS resolution"""
        return self.ens_cache.get(ens_name, "")
    
    def update_balance_cache(self, user: str, balance: float):
        """Update balance cache and add fact"""
        self.balance_cache[user] = balance
        self.add_fact(f"(balance {user} {balance})")
    
    def update_ens_cache(self, ens_name: str, address: str):
        """Update ENS cache and add fact"""
        self.ens_cache[ens_name] = address
        self.add_fact(f"(ens-address {ens_name} {address})")
    
    def update_user_history(self, user: str, data: dict):
        """Update user history for MeTTa reasoning"""
        self.user_history[user] = data
        age_days = data.get('age_days', 0)
        self.add_fact(f"(user-age-days {user} {age_days})")
    
    def get_payment_reasoning(self, prompt: str, user: str) -> dict:
        """Use MeTTa reasoning for payment decisions"""
        
        # Add initial facts about payment request
        self.add_fact(f"(payment-request {user} \"{prompt}\")")
        
        # Reasoning steps
        reasoning_steps = []
        
        # Step 1: Parse intent
        reasoning_steps.append({
            "step": 1,
            "action": "parse-intent",
            "input": prompt,
            "metta_fact": f"(parse-intent \"{prompt}\")"
        })
        
        # Step 2: Check balance
        reasoning_steps.append({
            "step": 2,
            "action": "check-balance",
            "user": user,
            "metta_query": f"(query (balance {user}))"
        })
        
        # Step 3: Resolve ENS
        reasoning_steps.append({
            "step": 3,
            "action": "resolve-ens",
            "metta_query": "(query (resolve-ens ?))"
        })
        
        # Step 4: Safety assessment
        reasoning_steps.append({
            "step": 4,
            "action": "safety-check",
            "metta_query": f"(query (payment-safe {user} ? ?))"
        })
        
        return {
            "reasoning_steps": reasoning_steps,
            "facts_used": self.facts[-10:],
            "rules_applied": self.rules[-5:],
            "knowledge_graph_size": len(self.facts),
            "cache_status": {
                "ens_entries": len(self.ens_cache),
                "balance_entries": len(self.balance_cache)
            }
        }

# Initialize MeTTa Knowledge Graph
metta_kg = MeTTaKnowledgeGraph()

# ENS Payment Core with MeTTa Integration
class ENSPaymentCore:
    def __init__(self):
        self.w3_cache = {}
        
    def get_web3(self, chain_id: int) -> Web3:
        """Get Web3 instance for chain"""
        if chain_id not in self.w3_cache:
            config = CHAIN_CONFIG.get(chain_id)
            if not config:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            self.w3_cache[chain_id] = Web3(Web3.HTTPProvider(config["rpc"]))
        return self.w3_cache[chain_id]
    
    def parse_intent(self, prompt: str) -> Dict[str, Any]:
        """Parse payment intent from natural language"""
        prompt_lower = prompt.lower().strip()
        
        patterns = [
            r'send\s+(\d+(?:\.\d+)?)\s+usdc\s+to\s+([a-zA-Z0-9-]+\.eth)',
            r'pay\s+(\d+(?:\.\d+)?)\s+usdc\s+to\s+([a-zA-Z0-9-]+\.eth)',
            r'transfer\s+(\d+(?:\.\d+)?)\s+usdc\s+to\s+([a-zA-Z0-9-]+\.eth)',
            r'give\s+([a-zA-Z0-9-]+\.eth)\s+(\d+(?:\.\d+)?)\s+usdc'
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, prompt_lower)
            if match:
                if i == 3: 
                    amount = float(match.group(2))
                    recipient = match.group(1)
                else:
                    amount = float(match.group(1))
                    recipient = match.group(2)
                
                # Validation
                if amount <= 0:
                    return {
                        "success": False,
                        "error": "Amount must be greater than 0"
                    }
                
                if amount > 10000:
                    return {
                        "success": False,
                        "error": "Amount too large (max 10,000 USDC)"
                    }
                
                if not re.match(r'^[a-zA-Z0-9-]+\.eth$', recipient):
                    return {
                        "success": False,
                        "error": "Invalid ENS name format"
                    }
                
                return {
                    "success": True,
                    "amount": amount,
                    "recipient": recipient.lower(),
                    "token": "USDC"
                }
        
        return {
            "success": False,
            "error": "Could not parse payment command. Try: 'Send 5 USDC to vitalik.eth'"
        }
    
    async def resolve_ens(self, ens_name: str) -> Optional[str]:
        """Resolve ENS name to Ethereum address"""
        # Check MeTTa knowledge graph first
        cached_address = metta_kg.get_cached_ens(ens_name)
        if cached_address:
            return cached_address
        
        try:
            w3 = self.get_web3(1)  # Use mainnet for ENS
            ens_instance = ENS.from_web3(w3)
            address = ens_instance.address(ens_name)
            
            if address:
                # Update MeTTa knowledge graph
                metta_kg.update_ens_cache(ens_name, address)
                return address
            return None
            
        except Exception as e:
            print(f"ENS resolution error for {ens_name}: {e}")
            return None
    
    async def check_user_balance(self, user_address: str, chain_id: int) -> float:
        """Check user's USDC balance"""
        # Check MeTTa knowledge graph first
        cached_balance = metta_kg.get_cached_balance(user_address)
        if cached_balance > 0:
            return cached_balance
        
        try:
            w3 = self.get_web3(chain_id)
            config = CHAIN_CONFIG[chain_id]
            
            usdc_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "type": "function"
                }
            ]
            
            contract = w3.eth.contract(address=config["usdc"], abi=usdc_abi)
            balance = contract.functions.balanceOf(user_address).call()
            decimals = contract.functions.decimals().call()
            
            balance_float = balance / (10 ** decimals)
            
            # Update MeTTa knowledge graph
            metta_kg.update_balance_cache(user_address, balance_float)
            
            return balance_float
            
        except Exception as e:
            print(f"Balance check error: {e}")
            return 0.0
    
    async def prepare_transaction(self, from_addr: str, to_addr: str, amount: float, chain_id: int) -> Dict[str, Any]:
        """Prepare USDC transfer transaction"""
        try:
            w3 = self.get_web3(chain_id)
            config = CHAIN_CONFIG[chain_id]
            
            # USDC has 6 decimals
            amount_wei = int(amount * (10 ** 6))
            
            # Encode transfer function call
            function_signature = "0xa9059cbb"  
            
            # Encode recipient address (32 bytes)
            to_address_bytes = bytes.fromhex(to_addr[2:].zfill(64))
            
            # Encode amount (32 bytes)
            amount_bytes = amount_wei.to_bytes(32, byteorder='big')
            
            # Combine function signature + parameters
            transaction_data = function_signature + to_address_bytes.hex() + amount_bytes.hex()
            
            # Estimate gas
            try:
                gas_estimate = w3.eth.estimate_gas({
                    'to': config["usdc"],
                    'from': from_addr,
                    'data': transaction_data
                })
            except Exception:
                gas_estimate = 100000  # Fallback gas limit
            
            return {
                "to": config["usdc"],
                "data": transaction_data,
                "value": "0x0",
                "gasLimit": hex(gas_estimate),
                "chainId": hex(chain_id)
            }
            
        except Exception as e:
            raise Exception(f"Transaction preparation failed: {e}")
    
    async def handle_payment_request(self, prompt: str, user_address: str, chain_id: int) -> Dict[str, Any]:
        """Main handler using MeTTa Knowledge Graph reasoning"""
        
        # Initialize MeTTa reasoning
        metta_reasoning = metta_kg.get_payment_reasoning(prompt, user_address)
        
        # Step 1: Parse intent
        intent = self.parse_intent(prompt)
        if not intent["success"]:
            return {
                **intent,
                "metta_reasoning": metta_reasoning,
                "knowledge_graph": metta_kg.facts[-5:]
            }
        
        # Step 2: MeTTa query for ENS validation
        ens_query = f"(query (resolve-ens {intent['recipient']}))"
        ens_result = metta_kg.query(ens_query)
        
        # Resolve ENS
        recipient_address = await self.resolve_ens(intent["recipient"])
        if not recipient_address:
            metta_kg.add_fact(f"(ens-resolution-failed {intent['recipient']})")
            return {
                "success": False,
                "error": f"Could not resolve ENS name: {intent['recipient']}",
                "metta_reasoning": metta_reasoning,
                "metta_query_result": ens_result,
                "knowledge_graph": metta_kg.facts[-5:]
            }
        
        # Step 3: Check balance and update knowledge graph
        user_balance = await self.check_user_balance(user_address, chain_id)
        
        # Step 4: MeTTa query for payment safety
        can_pay_query = f"(query (can-pay {user_address} {intent['amount']}))"
        can_pay_result = metta_kg.query(can_pay_query)
        
        if "insufficient-balance" in str(can_pay_result):
            return {
                "success": False,
                "error": f"Insufficient balance. You have {user_balance:.2f} USDC, need {intent['amount']} USDC",
                "metta_reasoning": metta_reasoning,
                "metta_query_result": can_pay_result,
                "knowledge_graph": metta_kg.facts[-5:]
            }
        
        # Step 5: Suspicious pattern detection
        suspicious_query = f"(query (suspicious-pattern {user_address} {intent['amount']}))"
        suspicious_result = metta_kg.query(suspicious_query)
        
        # Step 6: Prepare transaction
        try:
            transaction = await self.prepare_transaction(
                user_address, recipient_address, intent["amount"], chain_id
            )
            
            # Add successful reasoning to knowledge graph
            metta_kg.add_fact(f"(payment-prepared {user_address} {intent['amount']} {intent['recipient']})")
            
            response = {
                "success": True,
                "intent": intent,
                "recipient_address": recipient_address,
                "user_balance": user_balance,
                "transaction": transaction,
                "summary": f"Send {intent['amount']} USDC to {intent['recipient']} ({recipient_address[:6]}...{recipient_address[-4:]})",
                "metta_reasoning": metta_reasoning,
                "metta_query_results": {
                    "ens_query": ens_result,
                    "can_pay_query": can_pay_result,
                    "suspicious_check": suspicious_result
                },
                "knowledge_graph": metta_kg.facts[-10:]
            }
            
            # Add warning if suspicious pattern detected
            if "suspicious-pattern" in str(suspicious_result):
                response["warning"] = "Unusual payment pattern detected. Please verify recipient."
            
            return response
            
        except Exception as e:
            metta_kg.add_fact(f"(payment-failed {user_address} {str(e)})")
            return {
                "success": False,
                "error": str(e),
                "metta_reasoning": metta_reasoning,
                "knowledge_graph": metta_kg.facts[-5:]
            }

# Initialize payment core
payment_core = ENSPaymentCore()

# Agent Protocol Handlers
@agent.on_message(model=PaymentRequest)
async def handle_payment_message(ctx: Context, sender: str, msg: PaymentRequest):
    """Handle incoming payment requests with MeTTa reasoning"""
    
    ctx.logger.info(f"📨 Payment request from {sender}")
    ctx.logger.info(f"💬 Prompt: {msg.prompt}")
    ctx.logger.info(f"👤 User: {msg.user_address}")
    ctx.logger.info(f"⛓️ Chain: {msg.chain_id}")
    
    try:
        result = await payment_core.handle_payment_request(
            msg.prompt, 
            msg.user_address, 
            msg.chain_id
        )
        
        if result["success"]:
            response = PaymentResponse(
                success=True,
                message=result["summary"],
                transaction=result["transaction"],
                recipient_address=result["recipient_address"],
                user_balance=result["user_balance"],
                metta_reasoning=result.get("metta_reasoning"),
                knowledge_graph=result.get("knowledge_graph")
            )
            ctx.logger.info(f"✅ Payment prepared with MeTTa reasoning")
        else:
            response = PaymentResponse(
                success=False,
                message=f"❌ {result['error']}",
                error=result["error"],
                metta_reasoning=result.get("metta_reasoning"),
                knowledge_graph=result.get("knowledge_graph")
            )
            ctx.logger.info(f"❌ Payment failed: {result['error']}")
            
    except Exception as e:
        response = PaymentResponse(
            success=False,
            message=f"❌ Internal error: {str(e)}",
            error=str(e)
        )
        ctx.logger.error(f"💥 Exception: {str(e)}")
    
    await ctx.send(sender, response)

@agent.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle natural language chat messages"""
    
    ctx.logger.info(f"💬 Chat message from {sender}: {msg.message}")
    
    message_lower = msg.message.lower()
    
    if "help" in message_lower:
        response = ChatResponse(
            message="""**ENS Pay Agent Help**
            
I can help you send USDC to ENS names using MeTTa Knowledge Graphs!

**Examples:**
- "Send 5 USDC to vitalik.eth"
- "Transfer 10 USDC to nick.eth"
- "Pay 25 USDC to ens.eth"

**Other commands:**
- "help" - Show this help
- "balance" - Check your USDC balance
- "status" - Agent information
- "knowledge" - View knowledge graph stats

**MeTTa Features:**
- Smart caching of ENS names and balances
- Reasoning about payment safety
- Learning from transaction patterns"""
        )
    
    elif "balance" in message_lower:
        if not msg.user_id:
            response = ChatResponse(
                message="❌ Please provide your wallet address to check balance",
                requires_wallet=True
            )
        else:
            try:
                balance = await payment_core.check_user_balance(msg.user_id, 11155111)
                balance_query = f"(query (balance {msg.user_id}))"
                metta_result = metta_kg.query(balance_query)
                
                response = ChatResponse(
                    message=f""" **Your USDC Balance: {balance:.2f} USDC**
                    
    MeTTa Knowledge: {len(metta_kg.facts)} facts, {len(metta_kg.ens_cache)} ENS cached
    Balance cached: {'Yes' if msg.user_id in metta_kg.balance_cache else 'No'}"""
                )
            except Exception as e:
                response = ChatResponse(
                    message=f" Could not check balance: {str(e)}"
                )
    
    elif "knowledge" in message_lower:
        kg_stats = {
            "total_facts": len(metta_kg.facts),
            "total_rules": len(metta_kg.rules),
            "ens_cached": len(metta_kg.ens_cache),
            "balances_cached": len(metta_kg.balance_cache),
            "recent_facts": metta_kg.facts[-3:] if metta_kg.facts else []
        }
        
        response = ChatResponse(
            message=f""" **MeTTa Knowledge Graph Stats**
            
**Knowledge Base:**
- Total Facts: {kg_stats['total_facts']}
- Total Rules: {kg_stats['total_rules']}
- ENS Names Cached: {kg_stats['ens_cached']}
- Balances Cached: {kg_stats['balances_cached']}

**Recent Facts:**
{chr(10).join(['• ' + fact for fact in kg_stats['recent_facts']])}

The knowledge graph learns from every interaction!"""
        )
    
    elif "status" in message_lower:
        response = ChatResponse(
            message=f""" **ENS Pay Agent Status**
            
 **Agent Info:**
- Name: ENS Pay Agent with MeTTa
- Address: {agent.address}
- Status: Online  

 **Blockchain Support:**
- Ethereum Mainnet
- Polygon
- Sepolia Testnet

  **MeTTa Knowledge Graph:**
- Facts: {len(metta_kg.facts)}
- Rules: {len(metta_kg.rules)}
- Learning: Active  

 **Token Support:**
- USDC (all chains)"""
        )
    
    elif any(word in message_lower for word in ["send", "pay", "transfer"]):
        if not msg.user_id:
            response = ChatResponse(
                message=" Please connect your wallet to send payments",
                requires_wallet=True
            )
        else:
            result = await payment_core.handle_payment_request(
                msg.message, 
                msg.user_id, 
                11155111
            )
            
            if result["success"]:
                metta_info = result.get("metta_reasoning", {})
                knowledge_size = metta_info.get("knowledge_graph_size", 0)
                
                response = ChatResponse(
                    message=f"""✅ {result['summary']}

    **MeTTa Reasoning Applied:**
- Knowledge Graph: {knowledge_size} facts used
- ENS Resolution: {'Cached' if result.get('recipient_address') in metta_kg.ens_cache.values() else 'New lookup'}
- Balance Check: {'Cached' if msg.user_id in metta_kg.balance_cache else 'Fresh check'}

    Please approve the transaction in your wallet""",
                    transaction_data=result["transaction"]
                )
            else:
                response = ChatResponse(
                    message=f"❌ {result['error']}"
                )
    
    else:
        response = ChatResponse(
            message="""💡 I didn't understand that command.

**Try:**
- "Send 5 USDC to vitalik.eth"
- "help" for more options
- "balance" to check your USDC balance
- "knowledge" to see MeTTa stats"""
        )
    
    await ctx.send(sender, response)

@agent.on_query(model=AgentInfoQuery)
async def handle_info_query(ctx: Context, sender: str, _msg: AgentInfoQuery):
    """Handle queries about agent capabilities"""
    
    return AgentInfoResponse(
        name="ENS Pay Agent with MeTTa Knowledge Graphs",
        description="Send USDC to ENS names using natural language commands with MeTTa symbolic reasoning",
        capabilities=[
            "ENS name resolution with caching",
            "USDC balance checking with MeTTa facts", 
            "Transaction preparation with safety reasoning",
            "Multi-chain support (Ethereum, Polygon, Sepolia)",
            "MeTTa Knowledge Graph reasoning",
            "Suspicious pattern detection",
            "Smart caching and learning"
        ],
        examples=[
            "Send 5 USDC to vitalik.eth",
            "Transfer 10 USDC to nick.eth",
            "Pay 25 USDC to ens.eth",
            "Check my balance",
            "Show knowledge graph stats"
        ]
    )

@agent.on_event("startup")
async def startup_event(ctx: Context):
    """Agent startup initialization"""
    ctx.logger.info(f"🚀 ENS Pay Agent with MeTTa started successfully")
    ctx.logger.info(f"📍 Agent address: {agent.address}")
    ctx.logger.info(f"💳 Agent wallet: {agent.wallet.address()}")
    ctx.logger.info(f"🌐 Supported chains: {list(CHAIN_CONFIG.keys())}")
    ctx.logger.info(f"🧠 MeTTa Knowledge Graph initialized with {len(metta_kg.rules)} rules")

@agent.on_event("shutdown")
async def shutdown_event(ctx: Context):
    """Agent shutdown cleanup"""
    ctx.logger.info(f"🛑 ENS Pay Agent shutting down")
    ctx.logger.info(f"🧠 Final knowledge graph: {len(metta_kg.facts)} facts stored")

app = Flask(__name__)

@app.route('/endpoint', methods=['POST'])
def handle_http_request():
    """HTTP endpoint for Agentverse integration"""
    try:
        data = request.json
        if 'prompt' in data:
            result = asyncio.run(payment_core.handle_payment_request(
                data['prompt'],
                data.get('user_address', ''),
                data.get('chain_id', 11155111)
            ))
        elif 'message' in data:
            result = {
                'success': True,
                'message': f"Received chat: {data['message']}",
                'metta_knowledge_size': len(metta_kg.facts)
            }
        else:
            result = {
                'success': False,
                'error': 'Send PaymentRequest with prompt, user_address, chain_id'
            }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'agent': 'ENS Pay Agent with MeTTa',
        'version': '1.0.0',
        'metta_knowledge_graph': {
            'facts': len(metta_kg.facts),
            'rules': len(metta_kg.rules),
            'ens_cached': len(metta_kg.ens_cache),
            'balances_cached': len(metta_kg.balance_cache)
        }
    })

@app.route('/knowledge-graph', methods=['GET'])
def get_knowledge_graph():
    """Expose MeTTa knowledge graph"""
    return jsonify({
        'facts': metta_kg.facts,
        'rules': metta_kg.rules,
        'total_facts': len(metta_kg.facts),
        'total_rules': len(metta_kg.rules),
        'ens_cache': metta_kg.ens_cache,
        'balance_cache': metta_kg.balance_cache,
        'user_history': metta_kg.user_history
    })

@app.route('/metta-query', methods=['POST'])
def metta_query():
    """Query the MeTTa knowledge graph"""
    try:
        data = request.json
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'error': 'Query parameter required'
            }), 400
        
        results = metta_kg.query(query)
        
        return jsonify({
            'query': query,
            'results': results,
            'knowledge_graph_size': len(metta_kg.facts),
            'timestamp': asyncio.get_event_loop().time()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/add-fact', methods=['POST'])
def add_metta_fact():
    """Add fact to MeTTa knowledge graph"""
    try:
        data = request.json
        fact = data.get('fact', '')
        
        if not fact:
            return jsonify({
                'error': 'Fact parameter required'
            }), 400
        
        metta_kg.add_fact(fact)
        
        return jsonify({
            'success': True,
            'fact_added': fact,
            'total_facts': len(metta_kg.facts)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/recent-reasoning', methods=['GET'])
def get_recent_reasoning():
    """Get recent MeTTa reasoning examples"""
    recent_facts = metta_kg.facts[-20:] if len(metta_kg.facts) > 20 else metta_kg.facts
    
    return jsonify({
        'recent_facts': recent_facts,
        'sample_queries': [
            '(query (can-pay user123 5))',
            '(query (resolve-ens vitalik.eth))',
            '(query (payment-safe user123 5 vitalik.eth))',
            '(query (suspicious-pattern user123 1000))'
        ],
        'reasoning_examples': [
            {
                'scenario': 'User wants to send 5 USDC',
                'metta_steps': [
                    '(parse-intent "Send 5 USDC to vitalik.eth")',
                    '(query (balance user123))',
                    '(query (can-pay user123 5))',
                    '(query (resolve-ens vitalik.eth))',
                    '(conclude (payment-safe user123 5 vitalik.eth))'
                ]
            }
        ]
    })

def run_flask():
    """Run Flask server"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    print("🤖 Starting ENS Pay Agent with MeTTa Knowledge Graphs...")
    print(f"📍 Agent Address: {agent.address}")
    print(f"💳 Wallet Address: {agent.wallet.address()}")
    print(f"🧠 MeTTa Knowledge Graph: {len(metta_kg.rules)} rules initialized")
    print("💡 Send PaymentRequest messages to interact")
    print("🌐 HTTP endpoints available for Agentverse integration")
    
    # Start Flask HTTP server in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 HTTP server started on port {os.environ.get('PORT', 8080)}")
    
    # Start uAgent
    agent.run()