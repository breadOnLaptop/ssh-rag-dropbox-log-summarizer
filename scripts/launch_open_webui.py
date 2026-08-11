import os
import socket
import subprocess
import platform

def get_local_ip():
    """Finds the local IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually connect; just used to find the active interface.
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def launch_app():
    # 1. Setup Paths (Cross-platform support, Path-Independent)
    # Get the directory where this script is located, then find the parent directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir) 
    
    is_windows = platform.system() == "Windows"

    # Look in both 'venv' and '.venv' just in case
    possible_venvs = ["venv", ".venv"]
    venv_executable = None

    for v in possible_venvs:
        if is_windows:
            test_path = os.path.join(base_dir, v, "Scripts", "open-webui.exe")
        else:
            test_path = os.path.join(base_dir, v, "bin", "open-webui")
            
        if os.path.exists(test_path):
            venv_executable = test_path
            break

    if not os.path.exists(venv_executable):
        print("❌ ERROR: Could not find the open-webui executable.")
        print(f"Looked for: {venv_executable}")
        print("Ensure this script is in the same folder as your '.venv' folder.")
        return

    # 2. Setup Environment Variables
    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"

    # 3. Generate URLs
    local_ip = get_local_ip()
    port = "8080"
    network_url = f"http://{local_ip}:{port}"
    local_url = f"http://localhost:{port}"

    print("="*50)
    print("🚀 STARTING OPEN WEBUI")
    print(f"🏠 Local Access: {local_url}")
    print(f"🌐 Network Access: {network_url}")
    print("="*50)
    print("💡 Note: If others cannot connect, check your Firewall settings.")
    print("💡 Ensure port 8080 is allowed through your firewall.\n")

    try:
        subprocess.run([venv_executable, "serve", "--host", "0.0.0.0", "--port", port], env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running the app: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    launch_app()
