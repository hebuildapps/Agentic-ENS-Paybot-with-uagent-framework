#!/usr/bin/env python3
"""
ENS Pay Agent - Entry point for render.com deployment
This file is specifically created for render.com deployment compatibility.
Now using Chat Protocol v0.3.0 for proper Agentverse integration.
"""

import sys
import os
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("Starting ENS Pay Agent via ens_payuagent.py...")
    print("Using Chat Protocol v0.3.0 for Agentverse integration")

    # Import and run the main agent
    from agent import agent

    print("Agent configured and ready for deployment")
    print("Chat Protocol v0.3.0 enabled for wallet integration")

    # Run the agent (this will handle all the Chat Protocol v0.3.0 setup)
    agent.run()