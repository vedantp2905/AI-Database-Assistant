import os
import platform
import subprocess
import sys
import socket

def detect_terminal():
    if platform.system() == "Windows":
        shell = os.environ.get("SHELL")
        if shell and "bash" in shell.lower():
            return "bash"  # Git Bash or similar
        if "pwsh" in sys.executable.lower() or "powershell" in sys.executable.lower():
            return "powershell"
        return "cmd"  # Default Windows Command Prompt
    else:
        return "unix"  # Unix-like shell (Linux/Mac)

def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0

def free_port(port):
    """Free a port by killing the process using it."""
    if platform.system() == "Windows":
        command = f"netstat -ano | findstr :{port}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True)
    else:
        command = f"lsof -t -i:{port}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)
        if result.stdout:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(f"kill -9 {pid}", shell=True)

def open_in_new_terminal(command):
    # Join the command list into a single string
    cmd_str = " ".join(command)
    # AppleScript to open a new Terminal window and run the command
    script = f'''
    tell application "Terminal"
        do script "cd '{os.getcwd()}'; source venv/bin/activate; {cmd_str}"
    end tell
    '''
    subprocess.Popen(['osascript', '-e', script])

def run_apps():
    ports = [8501, 8502]
    for port in ports:
        if is_port_in_use(port):
            print(f"Port {port} is in use. Freeing it...")
            free_port(port)

    terminal_type = detect_terminal()
    print(f"Detected terminal type: {terminal_type}")
    
    # Commands to run the Streamlit apps
    app1_command = ["streamlit", "run", "src/schema_app.py", "--server.port", "8501"]
    app2_command = ["streamlit", "run", "src/query_app.py", "--server.port", "8502"]

    try:
        if terminal_type in ["cmd", "unix", "bash"]:
            # Use subprocess.Popen for concurrent execution
            open_in_new_terminal(app1_command)
            open_in_new_terminal(app2_command)
        elif terminal_type == "powershell":
            # Use Start-Process for PowerShell
            open_in_new_terminal(app1_command)
            open_in_new_terminal(app2_command)
        else:
            print("Unsupported terminal type. Please run the apps manually in separate terminals:")
            print("streamlit run src/schema_app.py --server.port 8501")
            print("streamlit run src/query_app.py --server.port 8502")
    except Exception as e:
        print(f"An error occurred while launching the apps: {e}")

if __name__ == "__main__":
    run_apps()
