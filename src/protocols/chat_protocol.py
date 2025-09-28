from typing import Dict, Any, Optional, List
from uagents import Context

class ConversationState:
    """Track conversation state for better context"""
    def __init__(self):
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, user_id: str) -> Dict[str, Any]:
        """Get or create user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "conversation_history": [],
                "pending_transaction": None,
                "last_intent": None,
                "user_preferences": {},
                "session_start": None
            }
        return self.user_sessions[user_id]

    def add_message(self, user_id: str, message: str, response: str = None, intent: Dict = None):
        """Add message to conversation history"""
        session = self.get_session(user_id)
        session["conversation_history"].append({
            "user_message": message,
            "bot_response": response,
            "intent": intent,
            "timestamp": None  
        })

        if len(session["conversation_history"]) > 10:
            session["conversation_history"] = session["conversation_history"][-10:]

    def set_pending_transaction(self, user_id: str, transaction_data: Dict):
        """Set pending transaction for user"""
        session = self.get_session(user_id)
        session["pending_transaction"] = transaction_data

    def clear_pending_transaction(self, user_id: str):
        """Clear pending transaction"""
        session = self.get_session(user_id)
        session["pending_transaction"] = None

class ChatProtocol:
    """Enhanced chat protocol following uAgent standards"""

    def __init__(self, asi1_client=None, payment_core=None, metta_kg=None):
        self.asi1_client = asi1_client
        self.payment_core = payment_core
        self.metta_kg = metta_kg
        self.conversation_state = ConversationState()

    async def process_message(self, ctx: Context, sender: str, message: str, user_id: str = None) -> Dict[str, Any]:
        """Process incoming message with enhanced context"""

        ctx.logger.info(f"💬 Processing message from {sender}: {message[:50]}...")

        session = self.conversation_state.get_session(user_id or sender)

        intent_classification = await self._classify_intent(message)

        if intent_classification["type"] == "payment":
            response = await self._handle_payment_intent(ctx, sender, message, user_id, session)
        elif intent_classification["type"] == "query":
            response = await self._handle_query_intent(ctx, sender, message, user_id, session)
        elif intent_classification["type"] == "conversation":
            response = await self._handle_conversation_intent(ctx, sender, message, user_id, session)
        else:
            response = await self._handle_fallback_intent(ctx, sender, message, user_id, session)

        self.conversation_state.add_message(
            user_id or sender,
            message,
            response.get("message"),
            intent_classification
        )

        return response

    async def _classify_intent(self, message: str) -> Dict[str, Any]:
        """Classify message intent using ASI1 or pattern matching"""

        message_lower = message.lower()

        payment_keywords = ["send", "pay", "transfer", "give", "usdc", ".eth"]
        if any(keyword in message_lower for keyword in payment_keywords):
            return {"type": "payment", "confidence": 0.8}

        query_keywords = ["balance", "status", "help", "knowledge", "info", "how"]
        if any(keyword in message_lower for keyword in query_keywords):
            return {"type": "query", "confidence": 0.7}

        conversation_keywords = ["hello", "hi", "thanks", "what", "why", "explain"]
        if any(keyword in message_lower for keyword in conversation_keywords):
            return {"type": "conversation", "confidence": 0.6}

        return {"type": "unknown", "confidence": 0.3}

    async def _handle_payment_intent(self, ctx: Context, sender: str, message: str, user_id: str, session: Dict) -> Dict[str, Any]:
        """Handle payment-related messages"""

        if not user_id:
            return {
                "requires_wallet": True,
                "message_type": "wallet_required"
            }

        try:
            result = await self.payment_core.handle_payment_request(
                message, user_id, 11155111 
            )

            if result["success"]:
                self.conversation_state.set_pending_transaction(user_id, result["transaction"])

                confidence_indicator = "🔥" if result.get("confidence", 0) > 0.8 else "⚡"

                return {
                    "message": f"""{confidence_indicator} {result['summary']}

**Transaction Details:**
• Recipient: {result['recipient_address'][:6]}...{result['recipient_address'][-4:]}
• Your Balance: {result['user_balance']:.2f} USDC
• Parsing Method: {'ASI1 LLM' if result.get('confidence', 0) > 0.7 else 'Pattern Matching'}

**MeTTa Knowledge Applied:**
• Facts Used: {len(result.get('knowledge_graph', []))}
• ENS Cached: {'✅' if result.get('recipient_address') in (self.metta_kg.ens_cache.values() if self.metta_kg else []) else '🔍'}

Please approve the transaction in your wallet! 🚀""",
                    "transaction_data": result["transaction"],
                    "message_type": "transaction_ready"
                }
            else:
                return {
                    "message": f" {result['error']}",
                    "message_type": "payment_error",
                    "error_details": result.get("metta_reasoning")
                }

        except Exception as e:
            ctx.logger.error(f"Payment processing error: {e}")
            return {
                "message": " An error occurred while processing your payment. Please try again.",
                "message_type": "system_error"
            }

    async def _handle_query_intent(self, ctx: Context, sender: str, message: str, user_id: str, session: Dict) -> Dict[str, Any]:
        """Handle query/information requests"""

        message_lower = message.lower()

        if "balance" in message_lower:
            if not user_id:
                return {
                    "message": " Please connect your wallet to check your balance",
                    "requires_wallet": True,
                    "message_type": "wallet_required"
                }

            try:
                balance = await self.payment_core.check_user_balance(user_id, 11155111)
                return {
                    "message": f""" **Your USDC Balance: {balance:.2f} USDC**

**Knowledge Graph Status:**
• Total Facts: {len(self.metta_kg.facts) if self.metta_kg else 0}
• ENS Names Cached: {len(self.metta_kg.ens_cache) if self.metta_kg else 0}
• Your Data Cached: {'✅' if user_id in (self.metta_kg.balance_cache if self.metta_kg else {}) else '🔍'}""",
                    "message_type": "balance_info"
                }
            except Exception as e:
                return {
                    "message": f"❌ Could not retrieve balance: {str(e)}",
                    "message_type": "balance_error"
                }

        elif "help" in message_lower:
            return {
                "message": """ **ENS Pay Agent Help**

I can help you send USDC to ENS names using advanced AI!

** Payment Commands:**
• "Send 5 USDC to alice.eth"
• "Pay 10 USDC to nick.eth"
• "Transfer 25 USDC to ens.eth"

** Information Commands:**
• "balance" - Check your USDC balance
• "status" - Agent system information
• "knowledge" - View AI knowledge stats

** AI Features:**
• ASI1 LLM natural language understanding
• MeTTa symbolic reasoning for safety
• Smart caching for speed
• Learning from interactions""",
                "message_type": "help_info"
            }

        elif "status" in message_lower or "info" in message_lower:
            return {
                "message": f"""🚀 **ENS Pay Agent Status**

**🤖 Agent Information:**
• Status: Online ✅
• AI Model: ASI1 LLM + MeTTa Reasoning
• Supported Networks: Ethereum, Polygon, Sepolia

**🧠 Knowledge Graph:**
• Active Facts: {len(self.metta_kg.facts) if self.metta_kg else 0}
• Reasoning Rules: {len(self.metta_kg.rules) if self.metta_kg else 0}
• Learning Status: Active ✅

**💰 Token Support:**
• USDC on all supported chains""",
                "message_type": "status_info"
            }

        elif "knowledge" in message_lower:
            if self.metta_kg:
                recent_facts = self.metta_kg.facts[-3:] if self.metta_kg.facts else []
                return {
                    "message": f"""🧠 **MeTTa Knowledge Graph**

**📊 Statistics:**
• Total Facts: {len(self.metta_kg.facts)}
• Active Rules: {len(self.metta_kg.rules)}
• ENS Cache: {len(self.metta_kg.ens_cache)} entries
• Balance Cache: {len(self.metta_kg.balance_cache)} entries

**🔄 Recent Learning:**
{chr(10).join(['• ' + fact for fact in recent_facts]) if recent_facts else '• No recent facts'}

The AI learns from every interaction! 🚀""",
                    "message_type": "knowledge_info"
                }
            else:
                return {
                    "message": "⚠️ Knowledge graph not available",
                    "message_type": "system_error"
                }

        else:
            # Use ASI1 for complex queries
            if self.asi1_client:
                try:
                    ai_response = await self.asi1_client.generate_chat_response(
                        message,
                        context={"type": "query", "conversation_history": session["conversation_history"][-3:]}
                    )
                    return {
                        "message": f"🤖 {ai_response}",
                        "message_type": "ai_response"
                    }
                except Exception as e:
                    ctx.logger.error(f"ASI1 query response failed: {e}")

            return {
                "message": "❓ I'm not sure how to help with that. Try 'help' for available commands!",
                "message_type": "unknown_query"
            }

    async def _handle_conversation_intent(self, ctx: Context, sender: str, message: str, user_id: str, session: Dict) -> Dict[str, Any]:
        """Handle casual conversation using ASI1"""

        if self.asi1_client:
            try:
                ai_response = await self.asi1_client.generate_chat_response(
                    message,
                    context={
                        "type": "conversation",
                        "conversation_history": session["conversation_history"][-3:],
                        "agent_capabilities": "ENS payments, USDC transfers, blockchain assistance"
                    }
                )
                return {
                    "message": f"😊 {ai_response}",
                    "message_type": "conversation"
                }
            except Exception as e:
                ctx.logger.error(f"ASI1 conversation failed: {e}")

        # Fallback responses
        message_lower = message.lower()
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey"]):
            return {
                "message": "👋 Hello! I'm your ENS payment assistant. I can help you send USDC to ENS names using AI! Try 'help' to get started.",
                "message_type": "greeting"
            }
        elif any(thanks in message_lower for thanks in ["thank", "thanks"]):
            return {
                "message": "😊 You're welcome! Happy to help with your ENS payments anytime!",
                "message_type": "thanks"
            }
        else:
            return {
                "message": "🤔 I'm here to help with ENS payments! Try asking me to send USDC to an ENS name, or type 'help' for more options.",
                "message_type": "conversation_fallback"
            }

    async def _handle_fallback_intent(self, ctx: Context, sender: str, message: str, user_id: str, session: Dict) -> Dict[str, Any]:
        """Handle unclassified messages"""

        # Try ASI1 as last resort
        if self.asi1_client:
            try:
                ai_response = await self.asi1_client.generate_chat_response(
                    message,
                    context={"type": "fallback", "agent_purpose": "ENS payment assistant"}
                )
                return {
                    "message": f"🤖 {ai_response}",
                    "message_type": "ai_fallback"
                }
            except Exception as e:
                ctx.logger.error(f"ASI1 fallback failed: {e}")

        return {
            "message": """🤷‍♂️ I'm not sure what you're asking for.

**I can help you with:**
• Sending USDC to ENS names
• Checking your balance
• Explaining how ENS payments work

Try: "Send 5 USDC to alice.eth" or "help" for more options!""",
            "message_type": "fallback"
        }