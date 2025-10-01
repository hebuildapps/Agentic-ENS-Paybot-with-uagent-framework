import os
import asyncio
import logging
from dotenv import load_dotenv

from uagents import Agent, Context, Protocol
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

load_dotenv()

agent = Agent(
    name="ens-pay-agent",
    port=8000,
    seed="adult absorb acid always among actor about agree aerobic alcohol air ahead",
    endpoint=["https://agentic-ens-paybot-with-uagent-framework.onrender.com/submit"],
)

fund_agent_if_low(agent.wallet.address())

metta_kg = MeTTaKnowledgeGraph()
ens_resolver = ENSResolver(metta_kg=metta_kg)
asi1_client = ASI1Client(metta_kg=metta_kg)
singularity_client = SingularityClient(metta_kg=metta_kg) 
payment_core = PaymentCore(ens_resolver=ens_resolver, metta_kg=metta_kg, asi1_client=asi1_client, singularity_client=singularity_client)
chat_protocol = SimpleChatProtocol(asi1_client=asi1_client, payment_core=payment_core, metta_kg=metta_kg, singularity_client=singularity_client)
agentverse_chat_protocol = Protocol("Chat Protocol v0.3.0")

# stage1 : Understanding
@agentverse_chat_protocol.on_message(model=ChatMessage)
async def handle_agentverse_chat(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"Chat message from {sender}: {msg.message}")

    try:
        result = await chat_protocol.handle_message(ctx, sender, msg.message, msg.user_id)
        '''sender's wallet address needed to be logged!!!!!!'''
        response = ChatResponse(
            message=result["message"],
            requires_wallet=result.get("requires_wallet", False), # why false?
            transaction_data=result.get("transaction_data")
        )

        await ctx.send(sender, response)

    except Exception as e:
        ctx.logger.error(f"Chat protocol error: {e}")
        response = ChatResponse(
            message="We encountered an error processing your message. Please try again."
        )
        await ctx.send(sender, response)

agent.include(agentverse_chat_protocol)

# stage3 : Execution
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


@agent.on_event("startup")
async def startup_event(ctx: Context):
    """Agent startup initialization"""
    ctx.logger.info(f"ENS Pay Agent with MeTTa started successfully")
    ctx.logger.info(f"Agent address: {agent.address}")
    ctx.logger.info(f"Agent wallet: {agent.wallet.address()}") ## in here - what you mean  -  agent wallet address? ~ is it sender's??
    ctx.logger.info(f"Supported chains: [1, 137, 11155111]") ## multi-chain support - need base, ethereum, polygon, sepolia
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
    print("Send ChatMessage to interact via Chat Protocol v0.3.0")
    print("Agent ready for Agentverse integration")

    agent.run()
    