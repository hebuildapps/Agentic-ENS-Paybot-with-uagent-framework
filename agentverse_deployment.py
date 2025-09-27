import os
from uagents import Agent
from src.ens_payuagent import agent, PaymentRequest, PaymentResponse

AGENTVERSE_CONFIG = {
    "name": "ENS Pay uAgent",
    "description": "Send USDC to ENS names using natural language",
    "version": "1.0.0",
    "mailbox_key": os.getenv("AGENTVERSE_MAILBOX_KEY"),
    "agent_address": agent.address,
    "protocols": ["payment", "ens", "usdc"],
    "public": True
}

def get_agent_for_agentverse():
    """Return configured agent for Agentverse deployment"""
    return agent

if __name__ == "__main__":
    print(f" 1] ENS Pay Agent ready for Agentverse deployment")
    print(f" 2] Agent Address: {agent.address}")
    print(f" 3] Mailbox Key Required: {AGENTVERSE_CONFIG['mailbox_key'] is not None}")
    
    agent.run()