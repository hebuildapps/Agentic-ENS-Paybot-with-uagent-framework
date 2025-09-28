#!/usr/bin/env python3
"""
ENS Pay Agent - Entry point for render.com deployment
This file is specifically created for render.com deployment compatibility.
"""

import sys
import os
import threading
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Import all the components from agent.py
    from src.metta import MeTTaKnowledgeGraph
    from src.ens_resolver import ENSResolver
    from src.payment import PaymentCore
    from src.llm import ASI1Client
    from src.singularity import SingularityClient
    from web import create_app, run_flask_server

    print("Starting ENS Pay Agent via ens_payuagent.py...")

    # Initialize components
    metta_kg = MeTTaKnowledgeGraph()
    ens_resolver = ENSResolver(metta_kg=metta_kg)
    asi1_client = ASI1Client(metta_kg=metta_kg)
    singularity_client = SingularityClient(metta_kg=metta_kg)
    payment_core = PaymentCore(ens_resolver=ens_resolver, metta_kg=metta_kg, asi1_client=asi1_client, singularity_client=singularity_client)

    print(f"MeTTa Knowledge Graph initialized with {len(metta_kg.rules)} rules")
    print(f"AI Components loaded: ASI1 LLM, SingularityNET")

    # For render.com, we primarily run the Flask web server
    flask_app = create_app(payment_core=payment_core, metta_kg=metta_kg)
    port = int(os.environ.get('PORT', 8080))

    print(f"Starting HTTP server on port {port}")
    print("Available endpoints:")
    print(f"  - POST /endpoint (payment requests)")
    print(f"  - GET /health (health check)")
    print(f"  - GET /knowledge-graph (MeTTa data)")
    print(f"  - POST /metta-query (query MeTTa)")

    # Run Flask server directly (not in thread for render.com)
    run_flask_server(flask_app, port=port)