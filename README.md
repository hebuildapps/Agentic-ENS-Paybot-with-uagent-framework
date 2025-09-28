![Static Badge](https://img.shields.io/badge/GitHub-black?style=plastic&logo=github&link=https%3A%2F%2Fgithub.com%2Fhebuildapps%2FAgentic-ENS-Paybot-with-uagent-framework)


# MeTTaPay - ENS Pay Agent
AI agent which does your work of sending money to your friends on a simple prompt.
#### AI agent for sending USDC to ENS names using natural language, powered by MeTTa Knowledge Graphs and uAgents framework.

## Purpose

Send crypto payments using simple commands like "Send 5 USDC to alice.eth". The agent uses MeTTa symbolic reasoning for smart caching, pattern detection, and transparent decision-making.

## Features
- **Natural Language Processing**: "Send 5 USDC to vitalik.eth"
- **ENS Resolution**: Converts alice.eth → wallet address  
- **Multi-Chain**: Ethereum, Polygon, Sepolia
- **MeTTa Knowledge Graphs**: Symbolic reasoning with facts and rules
- **Smart Caching**: Remembers ENS names and balances
- **Safety Checks**: Detects suspicious patterns, validates amounts

## Usage

### Basic Commands
```
Send 5 USDC to vitalik.eth
Pay 10 USDC to nick.eth
Check my balance
Help
```

### API Endpoint
```bash
POST /endpoint
{
  "prompt": "Send 5 USDC to vitalik.eth",
  "user_address": "0x742C65D61A6a2b1E3eA6c9c5C0b6C7F8D9e1A0B2",
  "chain_id": 11155111
}
```

### MeTTa Queries
```bash
POST /metta-query
{
  "query": "(query (can-pay user123 5))"
}
```

## Installation

```bash
pip install uagents web3 ens flask python-dotenv
python ens_pay_agent.py
```

**Environment Variables:**
```env
RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
USDC_CONTRACT_ADDRESS=0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238
```

## MeTTa Knowledge Graph

The agent uses symbolic reasoning:
- **Facts**: `(balance user123 25.5)`, `(ens-address vitalik.eth 0x1234...)`
- **Rules**: `(= (can-pay ?user ?amount) (>= (balance ?user) ?amount))`
- **Queries**: `(query (payment-safe user123 5 vitalik.eth))`

## Endpoints
- `GET /health` - Health check
- `GET /knowledge-graph` - View MeTTa facts/rules
- `POST /metta-query` - Query knowledge graph
- `POST /endpoint` - Main payment processing

## Safety
- Non-custodial (your wallet, your keys)
- Amount limits (max 10,000 USDC)
- Pattern detection for suspicious activity
- Transaction approval required
