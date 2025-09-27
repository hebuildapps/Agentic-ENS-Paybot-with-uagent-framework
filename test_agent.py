import asyncio
from uagents import Model
from src.ens_payuagent import PaymentRequest, PaymentResponse, agent

async def test_payment_flow():
    """Test the payment agent locally"""
    
    print(" Testing ENS Pay Agent...")
    
    # Test cases
    test_cases = [
        {
            "prompt": "Send 1 USDC to vitalik.eth",
            "user_address": "0x18D1eb50fA3A91250217a7F74421283a12745586",
            "chain_id": 11155111,
            "expected": "success"
        },
        {
            "prompt": "Pay 0.5 USDC to ens.eth", 
            "user_address": "0x18D1eb50fA3A91250217a7F74421283a12745586",
            "chain_id": 11155111,
            "expected": "success"
        },
        {
            "prompt": "Send money to alice",
            "user_address": "0x18D1eb50fA3A91250217a7F74421283a12745586", 
            "chain_id": 11155111,
            "expected": "error"
        }
    ]
    
    from src.ens_payuagent import payment_core
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test['prompt']}")
        
        result = await payment_core.handle_payment_request(
            test["prompt"],
            test["user_address"], 
            test["chain_id"]
        )
        
        if test["expected"] == "success" and result["success"]:
            print(f" PASS - {result['summary']}")
        elif test["expected"] == "error" and not result["success"]:
            print(f" PASS - Error handled: {result['error']}")
        else:
            print(f" FAIL - Unexpected result: {result}")

if __name__ == "__main__":
    asyncio.run(test_payment_flow())