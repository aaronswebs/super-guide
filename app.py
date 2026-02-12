"""
Web UI for Azure Agent Framework Chat Bot
Flask-based web interface for turn-by-turn chat
"""

import os
import asyncio
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from agent import ChatBotAgent

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Global agent instance
chat_agent = None

# Store conversation history (in production, use a database)
conversation_history = []


def get_agent():
    """Get or create the chat agent instance"""
    global chat_agent
    if chat_agent is None:
        chat_agent = ChatBotAgent()
    return chat_agent


@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages from the web UI
    
    Expects JSON: {"message": "user message"}
    Returns JSON: {"response": "agent response", "success": true/false}
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400
        
        # Get the agent
        agent = get_agent()
        
        # Run the chat in an async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Initialize agent if needed
            if agent.agent is None:
                loop.run_until_complete(agent.initialize())
            
            # Get response
            response = loop.run_until_complete(agent.chat(user_message))
            
            # Store in conversation history
            conversation_history.append({
                'role': 'user',
                'content': user_message
            })
            conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            return jsonify({
                'success': True,
                'response': response
            })
            
        finally:
            loop.close()
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Handle streaming chat messages from the web UI
    
    Expects JSON: {"message": "user message"}
    Returns: Server-Sent Events stream
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400
        
        user_message = data['message'].strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400
        
        def generate():
            """Generator function for streaming response"""
            agent = get_agent()
            full_response = []
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize agent if needed
                if agent.agent is None:
                    loop.run_until_complete(agent.initialize())
                
                # Collect all chunks from the async generator
                async def collect_chunks():
                    chunks = []
                    async for chunk in agent.chat_stream(user_message):
                        chunks.append(chunk)
                    return chunks
                
                # Get all chunks
                chunks = loop.run_until_complete(collect_chunks())
                
                # Yield each chunk
                for chunk in chunks:
                    full_response.append(chunk)
                    yield f"data: {chunk}\n\n"
                
                # Store in conversation history
                conversation_history.append({
                    'role': 'user',
                    'content': user_message
                })
                conversation_history.append({
                    'role': 'assistant',
                    'content': ''.join(full_response)
                })
                
            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
            finally:
                loop.close()
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        print(f"Error in streaming chat endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    return jsonify({
        'success': True,
        'history': conversation_history
    })


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    global conversation_history
    conversation_history = []
    return jsonify({
        'success': True,
        'message': 'History cleared'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    agent = get_agent()
    
    return jsonify({
        'success': True,
        'status': 'healthy',
        'agent_initialized': agent.agent is not None,
        'agent_name': agent.agent_name
    })


if __name__ == '__main__':
    # Get Flask configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    print("=" * 60)
    print("Azure Agent Framework Chat Bot - Web UI")
    print("=" * 60)
    print(f"Server starting on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
