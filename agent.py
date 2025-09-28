import os
import asyncio
import threading
import logging
from dotenv import load_dotenv

from uagents import Agent, Context
from uagents.setup import fund_agent_if_low

from src.metta import MeTTaKnowledgeGraph
from src.ens_resolver import ENSResolver
from src.payment import PaymentCore
from src.llm import ASI1Client
from src.singularity import SingularityClient
from src.protocols import (
    PaymentRequest, PaymentResponse, ChatMessage, ChatResponse,
    AgentInfoQuery, AgentInfoResponse
)
from src.protocols.chat_protocol_simple import SimpleChatProtocol
from web import create_app, run_flask_server

load_dotenv()

agent = Agent(
    name="ens-pay-agent",
    port=8000,
    seed="ens-payment-agent-secret-seed-phrase",
    endpoint=["http://127.0.0.1:8000/submit"],
)

fund_agent_if_low(agent.wallet.address())

metta_kg = MeTTaKnowledgeGraph()
ens_resolver = ENSResolver(metta_kg=metta_kg)
asi1_client = ASI1Client(metta_kg=metta_kg)
singularity_client = SingularityClient(metta_kg=metta_kg) 
payment_core = PaymentCore(ens_resolver=ens_resolver, metta_kg=metta_kg, asi1_client=asi1_client, singularity_client=singularity_client)
chat_protocol = SimpleChatProtocol(asi1_client=asi1_client, payment_core=payment_core, metta_kg=metta_kg, singularity_client=singularity_client)

@agent.on_message(model=PaymentRequest)
async def handle_payment_message(ctx: Context, sender: str, msg: PaymentRequest):
    """Handle incoming payment requests with MeTTa reasoning"""

    ctx.logger.info(f"Payment request from {sender}")
    ctx.logger.info(f"Prompt: {msg.prompt}")
    ctx.logger.info(f"User: {msg.user_address}")
    ctx.logger.info(f"Chain: {msg.chain_id}")
    print(f"PROCESSING PAYMENT: {msg.prompt} from {sender}")

    try:
        result = await payment_core.handle_payment_request(
            msg.prompt,
            msg.user_address,
            msg.chain_id
        )

        if result["success"]:
            response = PaymentResponse(
                success=True,
                message=result["summary"],
                transaction=result["transaction"],
                recipient_address=result["recipient_address"],
                user_balance=result["user_balance"],
                metta_reasoning=result.get("metta_reasoning"),
                knowledge_graph=result.get("knowledge_graph")
            )
            ctx.logger.info(f"Payment prepared with MeTTa reasoning")
            print(f"SUCCESS: Transaction prepared for {result['summary']}")
        else:
            response = PaymentResponse(
                success=False,
                message=f"{result['error']}",
                error=result["error"],
                metta_reasoning=result.get("metta_reasoning"),
                knowledge_graph=result.get("knowledge_graph")
            )
            ctx.logger.info(f"Payment failed: {result['error']}")
            print(f"FAILED: {result['error']}")

    except Exception as e:
        response = PaymentResponse(
            success=False,
            message=f"Internal error: {str(e)}",
            error=str(e)
        )
        ctx.logger.error(f"Exception: {str(e)}")

    await ctx.send(sender, response)

@agent.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    """Handle natural language chat messages using simplified protocol"""

    ctx.logger.info(f"Chat message from {sender}: {msg.message}")
    print(f"CHAT: {msg.message} from {sender}")

    try:
        result = await chat_protocol.handle_message(ctx, sender, msg.message, msg.user_id)

        response = ChatResponse(
            message=result["message"],
            requires_wallet=result.get("requires_wallet", False),
            transaction_data=result.get("transaction_data")
        )

    except Exception as e:
        ctx.logger.error(f"Chat protocol error: {e}")
        response = ChatResponse(
            message="⚠️ I encountered an error processing your message. Please try again."
        )

    await ctx.send(sender, response)

@agent.on_event("startup")
async def startup_event(ctx: Context):
    """Agent startup initialization"""
    ctx.logger.info(f"ENS Pay Agent with MeTTa started successfully")
    ctx.logger.info(f"Agent address: {agent.address}")
    ctx.logger.info(f"Agent wallet: {agent.wallet.address()}")
    ctx.logger.info(f"Supported chains: [1, 137, 11155111]")
    ctx.logger.info(f"MeTTa Knowledge Graph initialized with {len(metta_kg.rules)} rules")

@agent.on_event("shutdown")
async def shutdown_event(ctx: Context):
    """Agent shutdown cleanup"""
    ctx.logger.info(f"ENS Pay Agent shutting down")
    ctx.logger.info(f"Final knowledge graph: {len(metta_kg.facts)} facts stored")

if __name__ == "__main__":
    print("Starting ENS Pay Agent with Enhanced AI Integration...")
    print(f"Agent Address: {agent.address}")
    print(f"Wallet Address: {agent.wallet.address()}")
    print(f"AI Components:")
    print(f"  - MeTTa Knowledge Graph: {len(metta_kg.rules)} rules initialized")
    print(f"  - ASI1 LLM: Enhanced with MeTTa context")
    print(f"  - SingularityNET: {len(singularity_client.ai_services)} AI services available")
    print("Send PaymentRequest messages to interact")
    print("HTTP endpoints available for Agentverse integration")

    # Start Flask server
    flask_app = create_app(payment_core=payment_core, metta_kg=metta_kg)
    flask_thread = threading.Thread(
        target=run_flask_server,
        args=(flask_app,),
        daemon=True
    )
    flask_thread.start()
    print(f"HTTP server started on port {os.environ.get('PORT', 8080)}")

    # Start uAgent
    agent.run()
    