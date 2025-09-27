import asyncio
import re
import json
import logging
from typing import Optional, Dict, Any
from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from web3 import Web3
from ens import ENS
import os
from dotenv import load_dotenv

class ChatMessage(Model):
    message: str
    user_id: Optional[str] = None

class ChatResponse(Model):
    message: str
    requires_wallet: bool = False
    transaction_data: Optional[Dict[str, Any]] = None

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

CHAIN_CONFIG = {
    1: {
        "name": "Ethereum",
        "rpc": "https://eth-mainnet.g.alchemy.com/v2/-f90eohkSQsMAAVyFJx6f",
        "usdc": "0xA0b86a33E6441d7aE36C7c4AF2ABfC92d11f8b99"
    },
    137: {
        "name": "Polygon",
        "rpc": "https://polygon-mainnet.g.alchemy.com/v2/-f90eohkSQsMAAVyFJx6f", 
        "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    },
    11155111: {
        "name": "Sepolia",
        "rpc": os.getenv("RPC_URL"),
        "usdc": os.getenv("USDC_CONTRACT_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    }
}

class ENSPaymentCore:
    def __init__(self):
        self.w3_cache = {}
        self.ens_cache = {}
        
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
        if ens_name in self.ens_cache:
            return self.ens_cache[ens_name]
        
        try:
            w3 = self.get_web3(1)
            ens_instance = ENS.from_web3(w3)
            address = ens_instance.address(ens_name)
            
            if address:
                self.ens_cache[ens_name] = address
                return address
            return None
            
        except Exception as e:
            print(f"ENS resolution error for {ens_name}: {e}")
            return None
    
    async def check_user_balance(self, user_address: str, chain_id: int) -> float:
        """Check user's USDC balance"""
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
            
            return balance / (10 ** decimals)
            
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
            
            # Encoded amount (32 bytes)
            amount_bytes = amount_wei.to_bytes(32, byteorder='big')
            
            # Combining function signature + parameters
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
        """Main handler for payment requests"""
    
        intent = self.parse_intent(prompt)
        if not intent["success"]:
            return intent
        
        recipient_address = await self.resolve_ens(intent["recipient"])
        if not recipient_address:
            return {
                "success": False,
                "error": f"Could not resolve ENS name: {intent['recipient']}"
            }
        
        user_balance = await self.check_user_balance(user_address, chain_id)
        if user_balance < intent["amount"]:
            return {
                "success": False,
                "error": f"Insufficient balance. You have {user_balance:.2f} USDC, need {intent['amount']} USDC"
            }
        
        try:
            transaction = await self.prepare_transaction(
                user_address, recipient_address, intent["amount"], chain_id
            )
            
            return {
                "success": True,
                "intent": intent,
                "recipient_address": recipient_address,
                "user_balance": user_balance,
                "transaction": transaction,
                "summary": f"Send {intent['amount']} USDC to {intent['recipient']} ({recipient_address[:6]}...{recipient_address[-4:]})"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

payment_core = ENSPaymentCore()

@agent.on_message(model=PaymentRequest)
async def handle_payment_message(ctx: Context, sender: str, msg: PaymentRequest):
    """Handle incoming payment requests"""
    
    ctx.logger.info(f" Payment request from {sender}")
    ctx.logger.info(f" Prompt: {msg.prompt}")
    ctx.logger.info(f" User: {msg.user_address}")
    ctx.logger.info(f"  Chain: {msg.chain_id}")
    
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
                user_balance=result["user_balance"]
            )
            ctx.logger.info(f" Payment prepared successfully")
        else:
            response = PaymentResponse(
                success=False,
                message=f" {result['error']}",
                error=result["error"]
            )
            ctx.logger.info(f" Payment failed: {result['error']}")
            
    except Exception as e:
        response = PaymentResponse(
            success=False,
            message=f"Internal error: {str(e)}",
            error=str(e)
        )
        ctx.logger.error(f"Exception: {str(e)}")
    
    await ctx.send(sender, response)

@agent.on_query(model=AgentInfoQuery)
async def handle_info_query(ctx: Context, sender: str, _msg: AgentInfoQuery):
    """Handle queries about agent capabilities"""
    return AgentInfoResponse(
        name="ENS Pay Agent",
        description="Send USDC to ENS names using natural language commands",
        capabilities=[
            "ENS name resolution",
            "USDC balance checking", 
            "Transaction preparation",
            "Multi-chain support (Ethereum, Polygon, Sepolia)"
        ],
        examples=[
            "Send 5 USDC to vitalik.eth",
            "Transfer 10 USDC to nick.eth",
            "Pay 25 USDC to ens.eth"
        ]
    )

@agent.on_event("startup")
async def startup_event(ctx: Context):
    """Agent startup initialization"""
    ctx.logger.info(f"🚀 ENS Pay Agent started successfully")
    ctx.logger.info(f"📍 Agent address: {agent.address}")
    ctx.logger.info(f"💳 Agent wallet: {agent.wallet.address()}")
    ctx.logger.info(f"🌐 Supported chains: {list(CHAIN_CONFIG.keys())}")

@agent.on_event("shutdown")
async def shutdown_event(ctx: Context):
    """Agent shutdown cleanup"""
    ctx.logger.info(f"🛑 ENS Pay Agent shutting down")

if __name__ == "__main__":
    print("🤖 Starting ENS Pay Agent...")
    print(f"📍 Agent Address: {agent.address}")
    print(f"💳 Wallet Address: {agent.wallet.address()}")
    print("💡 Send PaymentRequest messages to interact")
    
    agent.run()

@agent.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle natural language chat messages"""
    
    ctx.logger.info(f"💬 Chat message from {sender}: {msg.message}")
    
    message_lower = msg.message.lower()
    
    if "help" in message_lower:
        response = ChatResponse(
            message="""**ENS Pay Agent Help**"""
        )
    
    elif "balance" in message_lower:
        if not msg.user_id:
            response = ChatResponse(
                message="Please provide your wallet address to check balance",
                requires_wallet=True
            )
        else:
            try:
                balance = await payment_core.check_user_balance(msg.user_id, 11155111)
                response = ChatResponse(
                    message=f" Your USDC balance: {balance:.2f} USDC"
                )
            except Exception as e:
                response = ChatResponse(
                    message=f" Could not check balance: {str(e)}"
                )
    
    elif any(word in message_lower for word in ["send", "pay", "transfer"]):
        if not msg.user_id:
            response = ChatResponse(
                message="Please connect your wallet to send payments",
                requires_wallet=True
            )
        else:
            result = await payment_core.handle_payment_request(
                msg.message, 
                msg.user_id, 
                11155111
            )
            
            if result["success"]:
                response = ChatResponse(
                    message=f" {result['summary']}\n\n🔐 Please approve the transaction in your wallet",
                    transaction_data=result["transaction"]
                )
            else:
                response = ChatResponse(
                    message=f" {result['error']}"
                )
    
    else:
        response = ChatResponse(
            message="""I didn't understand that command.

Try:
- "Send 5 USDC to vitalik.eth"
- "help" for more options
- "balance" to check your USDC balance"""
        )
    
    await ctx.send(sender, response)