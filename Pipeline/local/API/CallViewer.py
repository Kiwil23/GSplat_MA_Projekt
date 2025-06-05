import os
import subprocess
import webbrowser
import time
import requests

def wait_for_server(url, timeout=60, interval=2):
    """Wartet, bis die URL erreichbar ist oder Timeout erreicht."""
    start_time = time.time()
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Server ist erreichbar: {url}")
                time.sleep(10)
                return True
        except requests.exceptions.ConnectionError:
            pass  # Server noch nicht erreichbar
        if time.time() - start_time > timeout:
            print("Timeout erreicht, Server nicht erreichbar.")
            return False
        time.sleep(interval)

def main():
    viewer_path = os.path.join("..", "..", "..", "superSplatViewer")
    process = subprocess.Popen(
        ["npm", "run", "develop"],
        cwd=viewer_path,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    server_url = "http://localhost:3000"
    if wait_for_server(server_url, timeout=120):
        webbrowser.open(server_url)
    else:
        print("Fehler: Server nicht gestartet.")

if __name__ == "__main__":
    main()
