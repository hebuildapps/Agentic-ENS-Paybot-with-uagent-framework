import asyncio
from uagents import Model
from uagents.communication import send_message

class PaymentRequest(Model):
    prompt: str
    user_address: str
    chain_id: int = 11155111

async def test_agent():
    agent_address = "agent1q2sk7733pmd2drypm8njx9066yvh8002xjrgyun26t5nhsqkz5awstfy3x7"
    
    request = PaymentRequest(
        prompt="Send 1 USDC to vitalik.eth",
        user_address="0x18D1eb50fA3A91250217a7F74421283a12745586",
        chain_id=11155111
    )
    
    response = await send_message(agent_address, request)
    print("Response:", response)

if __name__ == "__main__":
    asyncio.run(test_agent())