#!/usr/bin/env python3
"""
ENS Pay Agent - Entry point for render.com deployment
This file is specifically created for render.com deployment compatibility.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Import and run the main agent
    from agent import agent

    print("Starting ENS Pay Agent via ens_payuagent.py...")
    print(f"Agent Address: {agent.address}")
    print(f"Wallet Address: {agent.wallet.address()}")

    # The agent.py module already contains all the startup logic
    # Just need to trigger the main execution
    import agent