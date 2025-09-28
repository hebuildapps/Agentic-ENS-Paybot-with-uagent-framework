import os
import asyncio
from flask import Flask, request, jsonify

def create_app(payment_core=None, metta_kg=None):
    """Create Flask app with endpoints"""
    app = Flask(__name__)

    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint - landing page"""
        return jsonify({
            'agent': 'ENS Pay Agent with MeTTa Knowledge Graph',
            'description': 'AI agent for blockchain payments using ENS names and MeTTa reasoning',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'POST /endpoint': 'Main payment processing endpoint',
                'GET /health': 'Health check',
                'GET /knowledge-graph': 'View MeTTa knowledge graph',
                'POST /metta-query': 'Query MeTTa knowledge',
                'POST /add-fact': 'Add facts to knowledge graph',
                'GET /recent-reasoning': 'View recent reasoning examples'
            },
            'usage': 'Send POST to /endpoint with {"prompt": "Pay 5 USDC to vitalik.eth", "user_address": "0x...", "chain_id": 11155111}',
            'metta_status': {
                'facts': len(metta_kg.facts) if metta_kg else 0,
                'rules': len(metta_kg.rules) if metta_kg else 0,
                'ens_cached': len(metta_kg.ens_cache) if metta_kg else 0
            }
        })

    @app.route('/endpoint', methods=['POST'])
    def handle_http_request():
        """HTTP endpoint for Agentverse integration"""
        try:
            data = request.json
            if 'prompt' in data:
                result = asyncio.run(payment_core.handle_payment_request(
                    data['prompt'],
                    data.get('user_address', ''),
                    data.get('chain_id', 11155111)
                ))
            elif 'message' in data:
                result = {
                    'success': True,
                    'message': f"Received chat: {data['message']}",
                    'metta_knowledge_size': len(metta_kg.facts) if metta_kg else 0
                }
            else:
                result = {
                    'success': False,
                    'error': 'Send PaymentRequest with prompt, user_address, chain_id'
                }

            return jsonify(result)

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'agent': 'ENS Pay Agent with MeTTa',
            'version': '1.0.0',
            'metta_knowledge_graph': {
                'facts': len(metta_kg.facts) if metta_kg else 0,
                'rules': len(metta_kg.rules) if metta_kg else 0,
                'ens_cached': len(metta_kg.ens_cache) if metta_kg else 0,
                'balances_cached': len(metta_kg.balance_cache) if metta_kg else 0
            }
        })

    @app.route('/knowledge-graph', methods=['GET'])
    def get_knowledge_graph():
        """Expose MeTTa knowledge graph"""
        if not metta_kg:
            return jsonify({'error': 'MeTTa knowledge graph not available'}), 404

        return jsonify({
            'facts': metta_kg.facts,
            'rules': metta_kg.rules,
            'total_facts': len(metta_kg.facts),
            'total_rules': len(metta_kg.rules),
            'ens_cache': metta_kg.ens_cache,
            'balance_cache': metta_kg.balance_cache,
            'user_history': metta_kg.user_history
        })

    @app.route('/metta-query', methods=['POST'])
    def metta_query():
        """Query the MeTTa knowledge graph"""
        if not metta_kg:
            return jsonify({'error': 'MeTTa knowledge graph not available'}), 404

        try:
            data = request.json
            query = data.get('query', '')

            if not query:
                return jsonify({
                    'error': 'Query parameter required'
                }), 400

            results = metta_kg.query(query)

            return jsonify({
                'query': query,
                'results': results,
                'knowledge_graph_size': len(metta_kg.facts),
                'timestamp': asyncio.get_event_loop().time()
            })

        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500

    @app.route('/add-fact', methods=['POST'])
    def add_metta_fact():
        """Add fact to MeTTa knowledge graph"""
        if not metta_kg:
            return jsonify({'error': 'MeTTa knowledge graph not available'}), 404

        try:
            data = request.json
            fact = data.get('fact', '')

            if not fact:
                return jsonify({
                    'error': 'Fact parameter required'
                }), 400

            metta_kg.add_fact(fact)

            return jsonify({
                'success': True,
                'fact_added': fact,
                'total_facts': len(metta_kg.facts)
            })

        except Exception as e:
            return jsonify({
                'error': str(e)
            }), 500

    @app.route('/recent-reasoning', methods=['GET'])
    def get_recent_reasoning():
        """Get recent MeTTa reasoning examples"""
        if not metta_kg:
            return jsonify({'error': 'MeTTa knowledge graph not available'}), 404

        recent_facts = metta_kg.facts[-20:] if len(metta_kg.facts) > 20 else metta_kg.facts

        return jsonify({
            'recent_facts': recent_facts,
            'sample_queries': [
                '(query (can-pay user123 5))',
                '(query (resolve-ens vitalik.eth))',
                '(query (payment-safe user123 5 vitalik.eth))',
                '(query (suspicious-pattern user123 1000))'
            ],
            'reasoning_examples': [
                {
                    'scenario': 'User wants to send 5 USDC',
                    'metta_steps': [
                        '(parse-intent "Send 5 USDC to vitalik.eth")',
                        '(query (balance user123))',
                        '(query (can-pay user123 5))',
                        '(query (resolve-ens vitalik.eth))',
                        '(conclude (payment-safe user123 5 vitalik.eth))'
                    ]
                }
            ]
        })

    return app

def run_flask_server(app, port=None):
    """Run Flask server"""
    if port is None:
        port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)