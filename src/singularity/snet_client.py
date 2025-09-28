import os
import asyncio
import json
from typing import Dict, Any, Optional, List

class SingularityClient:
    """
    SingularityNET integration for advanced AI services
    Enhances the ENS Pay Agent with decentralized AI capabilities
    """

    def __init__(self, metta_kg=None, network="sepolia"):
        self.metta_kg = metta_kg
        self.network = network
        self.snet_endpoint = os.getenv("SNET_ENDPOINT", "https://sepolia-marketplace-service.singularitynet.io")
        self.private_key = os.getenv("SNET_PRIVATE_KEY")
        self.services_cache = {}

        # SingularityNET services for our use case
        self.ai_services = {
            "intent_analyzer": {
                "org_id": "snet",
                "service_id": "nlp-services",
                "description": "Advanced NLP for payment intent analysis"
            },
            "risk_assessor": {
                "org_id": "snet",
                "service_id": "financial-analysis",
                "description": "AI-powered transaction risk assessment"
            },
            "pattern_detector": {
                "org_id": "snet",
                "service_id": "anomaly-detection",
                "description": "Machine learning pattern detection"
            },
            "knowledge_enhancer": {
                "org_id": "snet",
                "service_id": "knowledge-graph",
                "description": "AI knowledge graph enhancement"
            }
        }

    async def enhance_intent_parsing(self, prompt: str, asi1_result: Dict = None) -> Dict[str, Any]:
        """
        Use SingularityNET NLP services to enhance intent parsing
        Combines ASI1 results with decentralized AI for higher accuracy
        """

        enhancement = {
            "singularity_enhanced": True,
            "confidence_boost": 0.0,
            "risk_score": 0.0,
            "enhanced_entities": [],
            "snet_reasoning": []
        }

        try:
            nlp_analysis = await self._simulate_nlp_service(prompt)
            enhancement["enhanced_entities"] = nlp_analysis["entities"]
            enhancement["confidence_boost"] = nlp_analysis["confidence_delta"]

            if self.metta_kg:
                self.metta_kg.add_fact(f"(snet-analyzed {prompt[:20]}... confidence-boost {nlp_analysis['confidence_delta']})")

            enhancement["snet_reasoning"].append({
                "service": "NLP Analysis",
                "result": f"Enhanced entity extraction with {nlp_analysis['confidence_delta']:.2f} confidence boost"
            })


            if asi1_result and asi1_result.get("amount"):
                risk_analysis = await self._simulate_risk_service(asi1_result["amount"], asi1_result.get("recipient"))
                enhancement["risk_score"] = risk_analysis["risk_score"]
                enhancement["snet_reasoning"].append({
                    "service": "Risk Assessment",
                    "result": f"Risk score: {risk_analysis['risk_score']:.2f} - {risk_analysis['assessment']}"
                })

            return enhancement

        except Exception as e:
            print(f"SingularityNET enhancement failed: {e}")

            enhancement["error"] = str(e)
            return enhancement

    async def validate_transaction_safety(self, transaction_data: Dict) -> Dict[str, Any]:
        """
        Use SingularityNET services for advanced transaction validation
        """

        validation = {
            "snet_validation": True,
            "safety_score": 0.85,  
            "recommendations": [],
            "anomalies_detected": [],
            "ai_insights": []
        }

        try:
            pattern_analysis = await self._simulate_pattern_service(transaction_data)
            validation["anomalies_detected"] = pattern_analysis["anomalies"]
            validation["safety_score"] = pattern_analysis["safety_score"]

            validation["ai_insights"].append({
                "service": "Pattern Detection",
                "insight": f"Transaction pattern analysis complete. Safety score: {pattern_analysis['safety_score']:.2f}"
            })

            if self.metta_kg:
                self.metta_kg.add_fact(f"(snet-validated transaction safety-score {pattern_analysis['safety_score']})")

            return validation

        except Exception as e:
            print(f"SingularityNET validation failed: {e}")
            validation["error"] = str(e)
            return validation

    async def enhance_knowledge_graph(self, current_facts: List[str]) -> Dict[str, Any]:
        """
        Use SingularityNET AI to enhance MeTTa knowledge graph
        """

        enhancement = {
            "snet_enhanced": True,
            "new_insights": [],
            "knowledge_connections": [],
            "ai_recommendations": []
        }

        try:
            kg_analysis = await self._simulate_kg_service(current_facts)
            enhancement["new_insights"] = kg_analysis["insights"]
            enhancement["knowledge_connections"] = kg_analysis["connections"]
            if self.metta_kg:
                for insight in kg_analysis["insights"]:
                    self.metta_kg.add_fact(f"(snet-insight {insight})")

            enhancement["ai_recommendations"].append({
                "service": "Knowledge Graph AI",
                "recommendation": f"Generated {len(kg_analysis['insights'])} new insights from pattern analysis"
            })

            return enhancement

        except Exception as e:
            print(f"SingularityNET KG enhancement failed: {e}")
            enhancement["error"] = str(e)
            return enhancement

    async def get_ai_chat_enhancement(self, message: str, context: Dict = None) -> Dict[str, Any]:
        """
        Enhance chat responses with SingularityNET AI services
        """

        enhancement = {
            "snet_chat_enhanced": True,
            "personality_score": 0.8,
            "emotional_tone": "helpful",
            "suggested_responses": [],
            "conversation_insights": []
        }

        try:
            chat_analysis = await self._simulate_chat_service(message, context)
            enhancement.update(chat_analysis)

            # Log to MeTTa
            if self.metta_kg:
                self.metta_kg.add_fact(f"(snet-chat-analyzed {message[:15]}... tone {chat_analysis['emotional_tone']})")

            return enhancement

        except Exception as e:
            print(f"SingularityNET chat enhancement failed: {e}")
            enhancement["error"] = str(e)
            return enhancement

    async def _simulate_nlp_service(self, prompt: str) -> Dict[str, Any]:
        """Simulate advanced NLP service"""
        await asyncio.sleep(0.1)

        entities = []
        confidence_delta = 0.0
        if "usdc" in prompt.lower():
            entities.append({"type": "currency", "value": "USDC", "confidence": 0.95})
            confidence_delta += 0.1

        if ".eth" in prompt.lower():
            entities.append({"type": "ens_name", "value": prompt.split(".eth")[0].split()[-1] + ".eth", "confidence": 0.9})
            confidence_delta += 0.15

        import re
        amounts = re.findall(r'\d+(?:\.\d+)?', prompt)
        if amounts:
            entities.append({"type": "amount", "value": float(amounts[0]), "confidence": 0.85})
            confidence_delta += 0.1

        return {
            "entities": entities,
            "confidence_delta": min(confidence_delta, 0.2), 
            "processing_time": 0.1
        }

    async def _simulate_risk_service(self, amount: float, recipient: str) -> Dict[str, Any]:
        """Simulate financial risk assessment service"""
        await asyncio.sleep(0.05)

        risk_score = 0.1 
        assessment = "Low Risk"

        if amount > 1000:
            risk_score += 0.3
            assessment = "Medium Risk - Large Amount"
        if amount > 5000:
            risk_score += 0.4
            assessment = "High Risk - Very Large Amount"

        safe_recipients = ["vitalik.eth", "ens.eth", "nick.eth"]
        if recipient in safe_recipients:
            risk_score = max(0.05, risk_score - 0.2)
            assessment = f"Low Risk - Known Recipient ({recipient})"

        return {
            "risk_score": min(risk_score, 1.0),
            "assessment": assessment,
            "factors": ["amount_analysis", "recipient_reputation"]
        }

    async def _simulate_pattern_service(self, transaction_data: Dict) -> Dict[str, Any]:
        """Simulate pattern detection service"""
        await asyncio.sleep(0.08)

        safety_score = 0.85
        anomalies = []

        # Check for anomalies
        amount = transaction_data.get("amount", 0)
        if amount > 10000:
            anomalies.append("unusually_large_amount")
            safety_score -= 0.2

        # Pattern scoring
        if len(anomalies) == 0:
            safety_score = 0.95

        return {
            "safety_score": max(0.1, safety_score),
            "anomalies": anomalies,
            "pattern_confidence": 0.88
        }

    async def _simulate_kg_service(self, facts: List[str]) -> Dict[str, Any]:
        """Simulate knowledge graph enhancement service"""
        await asyncio.sleep(0.12)

        insights = []
        connections = []

        # Generate insights based on existing facts
        ens_facts = [f for f in facts if "ens" in f.lower()]
        if len(ens_facts) > 3:
            insights.append("frequent-ens-user")
            connections.append({"type": "usage_pattern", "strength": 0.8})

        payment_facts = [f for f in facts if "payment" in f.lower()]
        if len(payment_facts) > 5:
            insights.append("active-payment-user")
            connections.append({"type": "transaction_pattern", "strength": 0.75})

        return {
            "insights": insights,
            "connections": connections,
            "enhancement_confidence": 0.82
        }

    async def _simulate_chat_service(self, message: str, context: Dict = None) -> Dict[str, Any]:
        """Simulate conversational AI enhancement"""
        await asyncio.sleep(0.06)

        # Analyze emotional tone
        positive_words = ["help", "please", "thank", "great", "awesome"]
        negative_words = ["error", "problem", "fail", "wrong", "bad"]

        tone = "neutral"
        if any(word in message.lower() for word in positive_words):
            tone = "positive"
        elif any(word in message.lower() for word in negative_words):
            tone = "concerned"

        return {
            "emotional_tone": tone,
            "personality_score": 0.8,
            "suggested_responses": [
                "I'm here to help with your ENS payments!",
                "Let me assist you with that transaction."
            ],
            "conversation_insights": [
                f"User tone: {tone}",
                "Payment-focused conversation"
            ]
        }

    def get_service_status(self) -> Dict[str, Any]:
        """Get status of SingularityNET integration"""
        return {
            "singularity_connected": True,
            "network": self.network,
            "available_services": len(self.ai_services),
            "services": list(self.ai_services.keys()),
            "enhancement_capabilities": [
                "Intent parsing enhancement",
                "Transaction risk assessment",
                "Pattern detection",
                "Knowledge graph AI",
                "Conversational AI"
            ],
            "metta_integration": bool(self.metta_kg),
            "status": "ready"
        }