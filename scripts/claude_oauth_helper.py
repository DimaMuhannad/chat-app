import pty
import os
import select
import sys
import time
import re
import signal
import termios
import struct
import fcntl

URL_FILE = "/opt/chat-app/scratch/oauth_url.txt"
CODE_FILE = "/opt/chat-app/scratch/oauth_code.txt"
RESULT_FILE = "/opt/chat-app/scratch/oauth_result.txt"

os.makedirs("/opt/chat-app/scratch", exist_ok=True)
for f in [URL_FILE, CODE_FILE, RESULT_FILE]:
    if os.path.exists(f):
        try:
            os.remove(f)
        except OSError:
            pass

master, slave = pty.openpty()

# Set large terminal size (1000 cols) to avoid wrapping
winsize = struct.pack('HHHH', 50, 1000, 0, 0)
fcntl.ioctl(slave, termios.TIOCSWINSZ, winsize)

pid = os.fork()

if pid == 0:
    os.close(master)
    os.setsid()
    os.dup2(slave, 0)
    os.dup2(slave, 1)
    os.dup2(slave, 2)
    os.close(slave)
    os.environ['TERM'] = 'xterm-256color'
    os.environ['NODE_OPTIONS'] = '--max-old-space-size=1536'
    os.execlp('claude', 'claude', 'auth', 'login')

os.close(slave)

raw_output = b''
url_found = None

print("[OAuth Helper] Process started. Waiting for OAuth URL...")

start_time = time.time()
while time.time() - start_time < 30:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 2048)
            if not chunk:
                break
            raw_output += chunk
            clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_output.decode('utf-8', errors='ignore'))
            m = re.search(r'(https://claude\.com/cai/oauth/authorize\?[^\s\r\n]+)', clean_text)
            if m and not url_found:
                url_found = m.group(1).strip()
                print(f"[OAuth Helper] Found full URL: {url_found}")
                with open(URL_FILE, 'w') as uf:
                    uf.write(url_found + '\n')
            if 'Paste' in clean_text:
                if url_found:
                    print("[OAuth Helper] Prompt ready, waiting for code in oauth_code.txt...")
                    break
        except Exception as e:
            print(f"Read error: {e}")
            break

if not url_found:
    print("[OAuth Helper] Failed to capture URL")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    sys.exit(1)

# Wait up to 3600 seconds (1 hour) for CODE_FILE
code_received = None
wait_start = time.time()
while time.time() - wait_start < 3600:
    if os.path.exists(CODE_FILE):
        with open(CODE_FILE, 'r') as cf:
            content = cf.read().strip()
            if content:
                code_received = content
                break
    time.sleep(0.5)

if not code_received:
    print("[OAuth Helper] Timeout waiting for code (1 hour)")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    sys.exit(2)

print(f"[OAuth Helper] Received code (len={len(code_received)}). Submitting to CLI...")

code_clean = code_received.strip()
for ch in code_clean:
    os.write(master, ch.encode())
    time.sleep(0.005)
time.sleep(0.1)
os.write(master, b'\r')
time.sleep(0.1)
os.write(master, b'\n')

# Capture result for up to 30 seconds
result_output = b''
res_start = time.time()
while time.time() - res_start < 30:
    r, _, _ = select.select([master], [], [], 0.5)
    if r:
        try:
            chunk = os.read(master, 2048)
            if not chunk:
                break
            result_output += chunk
            clean_res = (raw_output + result_output).decode('utf-8', errors='ignore')
            if any(k in clean_res.lower() for k in ['logged in', 'success', 'token', 'welcome', 'error']):
                time.sleep(1)
                break
        except Exception:
            break

try:
    os.kill(pid, signal.SIGTERM)
except ProcessLookupError:
    pass

full_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', (raw_output + result_output).decode('utf-8', errors='ignore'))
with open(RESULT_FILE, 'w') as rf:
    rf.write(full_text)

print("[OAuth Helper] Completed. Output written to", RESULT_FILE)
