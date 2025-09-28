import os
import re
from typing import Dict, Any, Optional
from web3 import Web3

# Chain Config
CHAIN_CONFIG = {
    1: {
        "name": "Ethereum",
        "rpc": os.getenv("MAINNET_RPC"),
        "usdc": "0xA0b86a33E6441d7aE36C7c4AF2ABfC92d11f8b99"
    },
    137: {
        "name": "Polygon",
        "rpc": os.getenv("POLYGON_RPC"),
        "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    },
    11155111: {
        "name": "Sepolia",
        "rpc": os.getenv("RPC_URL"),
        "usdc": os.getenv("USDC_CONTRACT_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    }
}

class PaymentCore:
    def __init__(self, ens_resolver=None, metta_kg=None, asi1_client=None, singularity_client=None):
        self.w3_cache = {}
        self.ens_resolver = ens_resolver
        self.metta_kg = metta_kg
        self.asi1_client = asi1_client
        self.singularity_client = singularity_client

    def get_web3(self, chain_id: int) -> Web3:
        """Get Web3 instance for chain"""
        if chain_id not in self.w3_cache:
            config = CHAIN_CONFIG.get(chain_id)
            if not config:
                raise ValueError(f"Unsupported chain ID: {chain_id}")
            self.w3_cache[chain_id] = Web3(Web3.HTTPProvider(config["rpc"]))
        return self.w3_cache[chain_id]

    async def parse_intent(self, prompt: str, user_context: Dict = None) -> Dict[str, Any]:
        """Parse payment intent using enhanced ASI1-MeTTa pipeline"""

        # Build MeTTa context for ASI1
        metta_context = {}
        if self.metta_kg:
            metta_context = {
                'recent_facts': self.metta_kg.facts[-5:],
                'ens_cache': list(self.metta_kg.ens_cache.keys()),
                'user_history': self.metta_kg.user_history.get(user_context.get('user_id', ''), {})
            }

        # Try ASI1 LLM with MeTTa context
        if self.asi1_client:
            try:
                intent = await self.asi1_client.parse_payment_intent(prompt, metta_context)
                result = intent.to_dict()

                # Enhance with SingularityNET AI if available
                if self.singularity_client:
                    snet_enhancement = await self.singularity_client.enhance_intent_parsing(prompt, result)
                    result['singularity_enhanced'] = True
                    result['snet_confidence_boost'] = snet_enhancement.get('confidence_boost', 0.0)
                    result['snet_risk_score'] = snet_enhancement.get('risk_score', 0.0)
                    result['snet_reasoning'] = snet_enhancement.get('snet_reasoning', [])

                    # Apply confidence boost
                    if 'confidence' in result:
                        result['confidence'] = min(1.0, result['confidence'] + snet_enhancement.get('confidence_boost', 0.0))

                # Add MeTTa reasoning metadata
                result['parsing_method'] = 'ASI1+MeTTa+Singularity' if self.singularity_client else 'ASI1+MeTTa'
                result['metta_context_used'] = len(metta_context.get('recent_facts', []))

                return result
            except Exception as e:
                print(f"ASI1 parsing failed, using fallback: {e}")

        # Enhanced regex fallback
        result = self._regex_parse_intent(prompt)
        result['parsing_method'] = 'Regex+MeTTa'
        return result

    def _regex_parse_intent(self, prompt: str) -> Dict[str, Any]:
        """Fallback regex parsing method"""
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
                    "token": "USDC",
                    "confidence": 0.6  # Lower confidence for regex fallback
                }

        return {
            "success": False,
            "error": "Could not parse payment command. Try: 'Send 5 USDC to vitalik.eth'"
        }

    async def check_user_balance(self, user_address: str, chain_id: int) -> float:
        """Check user's USDC balance"""
        # Check MeTTa knowledge graph first
        if self.metta_kg:
            cached_balance = self.metta_kg.get_cached_balance(user_address)
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
            if self.metta_kg:
                self.metta_kg.update_balance_cache(user_address, balance_float)

            return balance_float

        except Exception as e:
            print(f"Balance check error: {e}")
            return 0.0

    async def prepare_transaction(self, from_addr: str, to_addr: str, amount: float, chain_id: int) -> Dict[str, Any]:
        """Prepare USDC transfer transaction"""
        try:
            w3 = self.get_web3(chain_id)
            config = CHAIN_CONFIG[chain_id]

            amount_wei = int(amount * (10 ** 6))

            function_signature = "0xa9059cbb"

            to_address_bytes = bytes.fromhex(to_addr[2:].zfill(64))

            amount_bytes = amount_wei.to_bytes(32, byteorder='big')

            transaction_data = function_signature + to_address_bytes.hex() + amount_bytes.hex()

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
        """Enhanced payment handler with integrated ASI1-MeTTa reasoning"""

        # Initialize MeTTa reasoning with enhanced context
        metta_reasoning = None
        if self.metta_kg:
            # Update user history for better reasoning
            self.metta_kg.update_user_history(user_address, {
                'last_request': prompt,
                'chain_id': chain_id,
                'age_days': 1  # Default for now, could be dynamic
            })
            metta_reasoning = self.metta_kg.get_payment_reasoning(prompt, user_address)

        # Parse intent with user context
        user_context = {'user_id': user_address, 'chain_id': chain_id}
        intent = await self.parse_intent(prompt, user_context)

        if not intent["success"]:
            # Enhanced error response with MeTTa insights
            error_response = {
                **intent,
                "metta_reasoning": metta_reasoning,
                "knowledge_graph": self.metta_kg.facts[-5:] if self.metta_kg else [],
                "parsing_insights": {
                    "method_used": intent.get('parsing_method', 'unknown'),
                    "context_available": bool(metta_reasoning)
                }
            }
            return error_response

        # Enhanced MeTTa query for ENS validation
        ens_query = f"(query (resolve-ens {intent['recipient']}))"
        ens_result = []
        ens_confidence_boost = 0.0

        if self.metta_kg:
            ens_result = self.metta_kg.query(ens_query)
            # Boost confidence if ENS is cached
            if intent['recipient'] in self.metta_kg.ens_cache:
                ens_confidence_boost = 0.1

        # Resolve ENS
        recipient_address = None
        if self.ens_resolver:
            recipient_address = await self.ens_resolver.resolve_ens(intent["recipient"])

        if not recipient_address:
            if self.metta_kg:
                self.metta_kg.add_fact(f"(ens-resolution-failed {intent['recipient']})")
            return {
                "success": False,
                "error": f"Could not resolve ENS name: {intent['recipient']}",
                "metta_reasoning": metta_reasoning,
                "metta_query_result": ens_result,
                "knowledge_graph": self.metta_kg.facts[-5:] if self.metta_kg else [],
                "resolution_insights": {
                    "ens_cache_checked": bool(self.metta_kg and intent['recipient'] in self.metta_kg.ens_cache),
                    "parsing_method": intent.get('parsing_method', 'unknown')
                }
            }

        # Check balance and update knowledge graph
        user_balance = await self.check_user_balance(user_address, chain_id)

        # Enhanced MeTTa query for payment safety with confidence scoring
        can_pay_query = f"(query (can-pay {user_address} {intent['amount']}))"
        can_pay_result = []
        payment_confidence = intent.get('confidence', 0.5) + ens_confidence_boost

        if self.metta_kg:
            can_pay_result = self.metta_kg.query(can_pay_query)

        if self.metta_kg and "insufficient-balance" in str(can_pay_result):
            return {
                "success": False,
                "error": f"Insufficient balance. You have {user_balance:.2f} USDC, need {intent['amount']} USDC",
                "metta_reasoning": metta_reasoning,
                "metta_query_result": can_pay_result,
                "knowledge_graph": self.metta_kg.facts[-5:] if self.metta_kg else [],
                "confidence_analysis": {
                    "parsing_confidence": intent.get('confidence', 0.5),
                    "ens_confidence_boost": ens_confidence_boost,
                    "final_confidence": payment_confidence
                }
            }

        # Suspicious pattern detection
        suspicious_query = f"(query (suspicious-pattern {user_address} {intent['amount']}))"
        suspicious_result = []
        if self.metta_kg:
            suspicious_result = self.metta_kg.query(suspicious_query)

        # Prepare transaction
        try:
            transaction = await self.prepare_transaction(
                user_address, recipient_address, intent["amount"], chain_id
            )

            # Validate transaction with SingularityNET AI
            snet_validation = {}
            if self.singularity_client:
                snet_validation = await self.singularity_client.validate_transaction_safety({
                    "amount": intent["amount"],
                    "recipient": intent["recipient"],
                    "user_address": user_address,
                    "transaction": transaction
                })

            if self.metta_kg:
                self.metta_kg.add_fact(f"(payment-prepared {user_address} {intent['amount']} {intent['recipient']})")

            response = {
                "success": True,
                "intent": intent,
                "recipient_address": recipient_address,
                "user_balance": user_balance,
                "transaction": transaction,
                "summary": f"Send {intent['amount']} USDC to {intent['recipient']} ({recipient_address[:6]}...{recipient_address[-4:]})",
                "confidence": payment_confidence,
                "metta_reasoning": metta_reasoning,
                "metta_query_results": {
                    "ens_query": ens_result,
                    "can_pay_query": can_pay_result,
                    "suspicious_check": suspicious_result
                },
                "knowledge_graph": self.metta_kg.facts[-10:] if self.metta_kg else [],
                "reasoning_pipeline": {
                    "parsing_method": intent.get('parsing_method', 'unknown'),
                    "metta_context_used": intent.get('metta_context_used', 0),
                    "ens_cached": intent['recipient'] in (self.metta_kg.ens_cache if self.metta_kg else {}),
                    "confidence_boosters": {
                        "ens_cache_hit": ens_confidence_boost,
                        "final_confidence": payment_confidence
                    }
                },
                "singularity_ai": snet_validation if snet_validation else {"status": "not_available"}
            }

            # Add warning if suspicious pattern detected
            if self.metta_kg and "suspicious-pattern" in str(suspicious_result):
                response["warning"] = "Unusual payment pattern detected. Please verify recipient."

            return response

        except Exception as e:
            if self.metta_kg:
                self.metta_kg.add_fact(f"(payment-failed {user_address} {str(e)})")
            return {
                "success": False,
                "error": str(e),
                "metta_reasoning": metta_reasoning,
                "knowledge_graph": self.metta_kg.facts[-5:] if self.metta_kg else [],
                "error_context": {
                    "parsing_method": intent.get('parsing_method', 'unknown'),
                    "stage_failed": "transaction_preparation"
                }
            }