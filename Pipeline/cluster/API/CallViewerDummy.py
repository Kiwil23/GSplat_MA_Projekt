import os
import subprocess
import shutil
import webbrowser
import time
def main():
    print("CallViewerDummy Cluster läuft")

    
    downloads_path = os.path.join(os.path.dirname(__file__), "downloads")



    viewer_path = os.path.join("..","..","..","superSplatViewer")
    dist_path = os.path.join(viewer_path,"dist")
    model_path = os.path.join(dist_path, "model")
    source_file = os.path.join(downloads_path, "splat.ply")
    target_file = os.path.join(model_path, "splat.ply")

    shutil.move(source_file, target_file)
    print(f"Datei verschoben nach: {target_file}")

    # npm-Befehl im Hintergrund starten
    process = subprocess.Popen(["npm", "run", "develop"], cwd=viewer_path,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(10)  

    webbrowser.open("http://localhost:3000")



if __name__ == "__main__":
    main()