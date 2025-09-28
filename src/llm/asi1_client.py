import os
import json
import httpx
from typing import Dict, Any, Optional, List

class PaymentIntent:
    def __init__(self, success: bool, amount: float = None, recipient: str = None,
                token: str = "USDC", error: str = None, confidence: float = 0.0):
        self.success = success
        self.amount = amount
        self.recipient = recipient
        self.token = token
        self.error = error
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "amount": self.amount,
            "recipient": self.recipient,
            "token": self.token,
            "error": self.error,
            "confidence": self.confidence
        }

    @classmethod
    def from_llm_response(cls, response_text: str, original_prompt: str):
        """Parse LLM response into PaymentIntent"""
        try:
            if response_text.strip().startswith('{'):
                data = json.loads(response_text)
                return cls(
                    success=data.get('success', False),
                    amount=data.get('amount'),
                    recipient=data.get('recipient'),
                    token=data.get('token', 'USDC'),
                    error=data.get('error'),
                    confidence=data.get('confidence', 0.8)
                )

            response_lower = response_text.lower()

            import re
            amount_match = re.search(r'amount[:\s]+(\d+(?:\.\d+)?)', response_lower)
            recipient_match = re.search(r'recipient[:\s]+([a-zA-Z0-9-]+\.eth)', response_lower)

            if amount_match and recipient_match:
                return cls(
                    success=True,
                    amount=float(amount_match.group(1)),
                    recipient=recipient_match.group(1),
                    confidence=0.7
                )

            return cls(
                success=False,
                error="ASI1 could not parse payment intent",
                confidence=0.0
            )

        except Exception as e:
            return cls(
                success=False,
                error=f"Failed to parse ASI1 response: {str(e)}",
                confidence=0.0
            )

class ASI1Client:
    def __init__(self, api_key: str = None, metta_kg=None):
        self.api_key = api_key or os.getenv("ASI1_API_KEY")
        self.base_url = "https://api.asi1.ai/v1"
        self.metta_kg = metta_kg
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def parse_payment_intent(self, prompt: str, metta_context: Dict = None) -> PaymentIntent:
        """Use ASI1 LLM to parse payment intent with MeTTa context"""

        metta_context_str = ""
        if metta_context and self.metta_kg:
            recent_facts = metta_context.get('recent_facts', [])
            cached_ens = list(self.metta_kg.ens_cache.keys())[:5]

            metta_context_str = f"""

MeTTa Knowledge Context:
- Known ENS names: {cached_ens}
- Recent facts: {recent_facts[-3:]}
- Use this context to improve parsing accuracy"""

        system_prompt = f"""You are an advanced payment intent parser with MeTTa symbolic reasoning integration.

Extract payment information from user messages and return a JSON object with these fields:
- success: boolean (true if payment intent found)
- amount: number (amount to send)
- recipient: string (ENS name like "vitalik.eth")
- token: string (always "USDC")
- error: string (if parsing failed)
- confidence: number (0.0-1.0, parsing confidence)
- reasoning: string (brief explanation of parsing logic)

Examples:
Input: "Send 5 USDC to alice.eth"
Output: {{"success": true, "amount": 5, "recipient": "alice.eth", "token": "USDC", "confidence": 0.95, "reasoning": "Clear payment command with valid ENS and amount"}}

Input: "Hello there"
Output: {{"success": false, "error": "No payment intent found", "confidence": 0.0, "reasoning": "Greeting message, no payment elements detected"}}

Validation rules:
- ENS names must end in .eth
- Amounts must be positive numbers
- Be more confident if recipient is in known ENS cache{metta_context_str}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "asi1-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 250
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    llm_response = data["choices"][0]["message"]["content"]
                    intent = PaymentIntent.from_llm_response(llm_response, prompt)

                    if self.metta_kg and intent.success:
                        self.metta_kg.add_fact(f"(asi1-parsed {prompt} {intent.amount} {intent.recipient} {intent.confidence})")

                    return intent
                else:
                    return PaymentIntent(
                        success=False,
                        error=f"ASI1 API error: {response.status_code}",
                        confidence=0.0
                    )

        except Exception as e:
            print(f"ASI1 API call failed: {e}")
            return self._fallback_metta_parse(prompt, metta_context)

    def _fallback_metta_parse(self, prompt: str, metta_context: Dict = None) -> PaymentIntent:
        """Enhanced fallback parsing with MeTTa reasoning"""
        if self.metta_kg and metta_context:
            similar_patterns = self._find_similar_patterns(prompt)
            if similar_patterns:
                confidence_boost = 0.1
            else:
                confidence_boost = 0.0
        else:
            confidence_boost = 0.0
        import re

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

                if amount <= 0:
                    return PaymentIntent(
                        success=False,
                        error="Amount must be greater than 0",
                        confidence=0.9
                    )

                if amount > 10000:
                    return PaymentIntent(
                        success=False,
                        error="Amount too large (max 10,000 USDC)",
                        confidence=0.9
                    )

                final_confidence = 0.6 + confidence_boost

                if self.metta_kg:
                    self.metta_kg.add_fact(f"(regex-parsed {prompt} {amount} {recipient.lower()} {final_confidence})")

                return PaymentIntent(
                    success=True,
                    amount=amount,
                    recipient=recipient.lower(),
                    confidence=final_confidence
                )

        if self.metta_kg:
            self.metta_kg.add_fact(f"(parse-failed {prompt})")

        return PaymentIntent(
            success=False,
            error="Could not parse payment command. Try: 'Send 5 USDC to vitalik.eth'",
            confidence=0.8
        )

    def _find_similar_patterns(self, prompt: str) -> List[str]:
        """Find similar parsing patterns in MeTTa knowledge"""
        if not self.metta_kg:
            return []

        similar = []
        for fact in self.metta_kg.facts:
            if "parsed" in fact and any(word in fact for word in prompt.lower().split()):
                similar.append(fact)
        return similar[:3] 

    async def generate_chat_response(self, message: str, context: dict = None, metta_insights: dict = None) -> str:
        """Generate conversational response using ASI1"""

        metta_context_str = ""
        if metta_insights and self.metta_kg:
            kg_stats = {
                "facts": len(self.metta_kg.facts),
                "rules": len(self.metta_kg.rules),
                "ens_cache": len(self.metta_kg.ens_cache)
            }
            recent_facts = self.metta_kg.facts[-3:] if self.metta_kg.facts else []

            metta_context_str = f"""

MeTTa Knowledge Context:
- Knowledge Base: {kg_stats['facts']} facts, {kg_stats['rules']} rules
- ENS Cache: {kg_stats['ens_cache']} entries
- Recent Learning: {recent_facts}
- Use this context to provide more informed responses"""

        system_prompt = f"""You are an advanced ENS payment assistant powered by MeTTa symbolic reasoning.

Key capabilities:
- Process payment commands like "Send 5 USDC to alice.eth"
- Check balances and provide helpful information
- Explain ENS names and USDC transactions with AI reasoning
- Learn from interactions to improve responses
- Be friendly, informative, and intelligent

Keep responses concise and helpful. Always mention that transactions need wallet approval.{metta_context_str}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "asi1-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 300
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    ai_response = data["choices"][0]["message"]["content"]

                    if self.metta_kg:
                        self.metta_kg.add_fact(f"(chat-response {message[:20]}... successful)")

                    return ai_response
                else:
                    return "I'm having trouble processing your request right now. Please try again."

        except Exception as e:
            print(f"ASI1 chat response failed: {e}")

            # Log failure to MeTTa
            if self.metta_kg:
                self.metta_kg.add_fact(f"(chat-failure {str(e)[:30]})")

            return "I'm experiencing technical difficulties. Please try your request again."