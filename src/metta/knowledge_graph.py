from typing import List, Dict, Any

class MeTTaKnowledgeGraph:
    def __init__(self):
        # Knowledge base as rules
        self.facts = []
        self.rules = []
        self.ens_cache = {}
        self.balance_cache = {}
        self.user_history = {}

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

            # Checks for suspicious patterns
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

        self.add_fact(f"(payment-request {user} \"{prompt}\")")

        reasoning_steps = []

        reasoning_steps.append({
            "step": 1,
            "action": "parse-intent",
            "input": prompt,
            "metta_fact": f"(parse-intent \"{prompt}\")"
        })

        reasoning_steps.append({
            "step": 2,
            "action": "check-balance",
            "user": user,
            "metta_query": f"(query (balance {user}))"
        })

        reasoning_steps.append({
            "step": 3,
            "action": "resolve-ens",
            "metta_query": "(query (resolve-ens ?))"
        })

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