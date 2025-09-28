from typing import Dict, Any, Optional
from uagents import Context

class SimpleChatProtocol:
    """Streamlined chat protocol focused on core functionality"""

    def __init__(self, asi1_client=None, payment_core=None, metta_kg=None, singularity_client=None):
        self.asi1_client = asi1_client
        self.payment_core = payment_core
        self.metta_kg = metta_kg
        self.singularity_client = singularity_client
        self.pending_transactions = {}

    async def handle_message(self, ctx: Context, sender: str, message: str, user_id: str = None) -> Dict[str, Any]:
        """Single entry point for all message handling"""

        ctx.logger.info(f"Processing message: {message}")
        ctx.logger.info(f"Sender: {sender}, User ID: {user_id}")

        message_lower = message.lower()

        if any(word in message_lower for word in ["send", "pay", "transfer", "usdc", ".eth"]):
            ctx.logger.info("Routing to payment handler")
            return await self._handle_payment(ctx, message, user_id or sender)

        elif any(word in message_lower for word in ["balance"]):
            return await self._handle_balance(ctx, user_id or sender)

        elif any(word in message_lower for word in ["help"]):
            return await self._handle_help()

        elif any(word in message_lower for word in ["status", "info"]):
            return await self._handle_status()

        elif any(word in message_lower for word in ["knowledge"]):
            return await self._handle_knowledge()

        else:
            return await self._handle_general_chat(ctx, message)

    async def _handle_payment(self, ctx: Context, message: str, user_id: str) -> Dict[str, Any]:
        """Handle payment requests - core functionality"""

        if not user_id:
            return {
                "message": "Please connect your wallet to process payments",
                "requires_wallet": True
            }

        try:
            result = await self.payment_core.handle_payment_request(message, user_id, 11155111)

            if result["success"]:
            
                self.pending_transactions[user_id] = result["transaction"]

                confidence_indicator = "HIGH" if result.get("confidence", 0) > 0.8 else "MEDIUM"

                # Format transaction data for Agentverse wallet integration
                transaction_data = {
                    "to": result["transaction"]["to"],
                    "data": result["transaction"]["data"],
                    "value": result["transaction"]["value"],
                    "gasLimit": result["transaction"]["gasLimit"],
                    "chainId": result["transaction"]["chainId"],
                    # Additional fields that might be required
                    "from": user_id,
                    "amount": str(result["intent"]["amount"]),
                    "token": "USDC",
                    "recipient": result["intent"]["recipient"],
                    "type": "erc20_transfer"
                }

                return {
                    "message": f"""Transaction ready: {result['summary']}

Your Balance: {result['user_balance']:.2f} USDC
AI Confidence: {result.get('confidence', 0):.1%} ({confidence_indicator})
Knowledge Used: {len(result.get('knowledge_graph', []))} facts

Please approve the transaction in your connected wallet.""",
                    "transaction_data": transaction_data,
                    "requires_wallet": True
                }
            else:
                return {
                    "message": f" {result['error']}"
                }

        except Exception as e:
            ctx.logger.error(f"Payment error: {e}")
            return {
                "message": "Payment processing failed. Please try again."
            }

    async def _handle_balance(self, ctx: Context, user_id: str) -> Dict[str, Any]:
        """Handle balance queries"""

        if not user_id:
            return {
                "message": " Please connect your wallet to check balance",
                "requires_wallet": True
            }

        try:
            balance = await self.payment_core.check_user_balance(user_id, 11155111)
            knowledge_size = len(self.metta_kg.facts) if self.metta_kg else 0

            return {
                "message": f""" **Balance: {balance:.2f} USDC**

Knowledge Graph: {knowledge_size} facts learned
Ready for payments on Sepolia testnet"""
            }
        except Exception as e:
            return {
                "message": f" Could not check balance: {str(e)}"
            }

    async def _handle_help(self) -> Dict[str, Any]:
        """Simple help response"""
        return {
            "message": """**ENS Pay Agent Help**

** Payment Commands:**
• "Send 5 USDC to alice.eth"
• "Pay 10 USDC to vitalik.eth"

** Info Commands:**
• "balance" - Check your USDC
• "status" - Agent info
• "knowledge" - AI stats

Powered by ASI1 LLM + MeTTa reasoning + SingularityNET AI! """
        }

    async def _handle_status(self) -> Dict[str, Any]:
        """Agent status info"""
        knowledge_stats = ""
        if self.metta_kg:
            knowledge_stats = f"""
 **AI Knowledge:**
• Facts: {len(self.metta_kg.facts)}
• Rules: {len(self.metta_kg.rules)}
• ENS Cache: {len(self.metta_kg.ens_cache)} entries"""


        snet_status = ""
        if self.singularity_client:
            snet_info = self.singularity_client.get_service_status()
            snet_status = f"""
**SingularityNET AI:**
• Services: {snet_info['available_services']} available
• Enhancements: Intent parsing, Risk assessment, Pattern detection
• Network: {snet_info['network']}"""

        return {
            "message": f"""**ENS Pay Agent Status**

 **Online & Ready**
• ASI1 LLM: Active
• MeTTa Reasoning: Active
• SingularityNET: {'Active' if self.singularity_client else 'Not configured'}
• Blockchain: Sepolia Testnet{knowledge_stats}{snet_status}

Ready to process USDC payments with AI enhancement! """
        }

    async def _handle_knowledge(self) -> Dict[str, Any]:
        """Knowledge graph stats"""
        if not self.metta_kg:
            return {
                "message": " Knowledge graph not available"
            }

        recent_facts = self.metta_kg.facts[-3:] if self.metta_kg.facts else []

        return {
            "message": f""" **AI Knowledge Stats**

 **Learning Progress:**
• Total Facts: {len(self.metta_kg.facts)}
• Active Rules: {len(self.metta_kg.rules)}
• ENS Cache: {len(self.metta_kg.ens_cache)} names
• Balance Cache: {len(self.metta_kg.balance_cache)} wallets

 **Recent Learning:**
{chr(10).join(['• ' + fact for fact in recent_facts]) if recent_facts else '• No recent facts'}

The AI learns from every interaction! """
        }

    async def _handle_general_chat(self, ctx: Context, message: str) -> Dict[str, Any]:
        """Handle general conversation using ASI1"""
        if self.asi1_client:
            try:
                ai_response = await self.asi1_client.generate_chat_response(
                    message,
                    context={"agent_type": "ENS payment assistant"},
                    metta_insights={"kg_available": bool(self.metta_kg)}
                )
                return {
                    "message": f"{ai_response}"
                }
            except Exception as e:
                ctx.logger.error(f"ASI1 chat failed: {e}")

        if any(word in message.lower() for word in ["hello", "hi", "hey"]):
            return {
                "message": " Hello! I'm your AI-powered ENS payment assistant. Try 'Send 5 USDC to alice.eth' or 'help' for options!"
            }
        elif any(word in message.lower() for word in ["thank", "thanks"]):
            return {
                "message": "You're welcome! Happy to help with ENS payments anytime!"
            }
        else:
            return {
                "message": """ I specialize in ENS payments with AI reasoning!

**Try:**
• "Send 5 USDC to vitalik.eth"
• "balance" to check your USDC
• "help" for more commands

Powered by ASI1 + MeTTa!"""
            }