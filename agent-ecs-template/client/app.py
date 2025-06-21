import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get server URL from environment
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8081')

@app.route('/health', methods=['GET'])
def health():
    # Check own health
    health_status = {
        "status": "healthy",
        "service": "client",
        "server_connectivity": "unknown"
    }
    
    # Try to connect to server health endpoint
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            health_status["server_connectivity"] = "connected"
            health_status["server_status"] = response.json()
        else:
            health_status["server_connectivity"] = "error"
            health_status["server_error"] = f"Server returned status {response.status_code}"
    except requests.exceptions.Timeout:
        health_status["server_connectivity"] = "timeout"
        health_status["server_error"] = "Server health check timed out"
    except requests.exceptions.ConnectionError:
        health_status["server_connectivity"] = "unreachable"
        health_status["server_error"] = "Cannot connect to server"
    except Exception as e:
        health_status["server_connectivity"] = "error"
        health_status["server_error"] = str(e)
    
    # If server is not connected, return 503 Service Unavailable
    if health_status["server_connectivity"] != "connected":
        return jsonify(health_status), 503
    
    return jsonify(health_status), 200

@app.route('/inquire', methods=['POST'])
def inquire():
    """Forward requests to the server"""
    try:
        # Get the request data
        data = request.get_json()
        
        # Forward to server
        response = requests.post(f"{SERVER_URL}/api/process", json=data)
        
        # Return server response
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "client",
        "endpoints": ["/health", "/inquire"],
        "server_url": SERVER_URL
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)