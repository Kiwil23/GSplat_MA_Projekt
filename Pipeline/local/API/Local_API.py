import os
import subprocess
import shutil
import time
from flask import Flask, request, send_file, abort
from threading import Thread, Lock
import argparse
import CallViewerDummy

app = Flask(__name__)

# Directories for uploaded and downloadable files
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'

# Ensure the directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Argument parser for configurable URL name for zrok tunnel
parser = argparse.ArgumentParser(description="Flask upload server with cluster integration")
parser.add_argument(
    "--url-name",
    default='splatscan777scapp777',
    help="Name of your reserved zrok URL"
)
args = parser.parse_args()

# Job control variables to prevent concurrent execution
job_running = False
job_lock = Lock()

is_splat_gen = False


def clear_directory(directory_path):
    """
    Delete all files and folders inside the given directory.
    Used to clean stale files on startup.
    """
    if os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")


def upload_and_monitor_job_dummy(save_path, keep_pre, keep_post, keep_train_img, iterations):
    """
    Simulate a job that processes uploaded data.
    Copies the first uploaded file to a workspace input directory,
    then runs a bash script with given parameters, streaming output.
    """
    

    global job_running
    with job_lock:
        job_running = True

    # Copy first file from upload directory to the workspace input directory
    entries = sorted(os.listdir(UPLOAD_FOLDER))
    for entry in entries:
        source_path = os.path.join(UPLOAD_FOLDER, entry)
        if os.path.isfile(source_path):
            dest_path = "../splat_workspace/input_data"
            os.makedirs(dest_path, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            print(f"File '{entry}' copied to {dest_path}.")
            break
    else:
        print("No files found in upload directory.")

    print(f"[Dummy] Starting local_job.sh with parameters: {keep_pre} {keep_post} {keep_train_img} {iterations}")

    cmd = [
        "bash",
        "../splat_workspace/local_job.sh",
        str(keep_pre),
        str(keep_post),
        str(keep_train_img),
        str(iterations)
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        # Stream live stdout
        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                print(f"[stdout] {output.strip()}")

        # Read remaining stderr output
        stderr_output = process.stderr.read()
        if stderr_output:
            print(f"[stderr] {stderr_output.strip()}")

        if process.returncode != 0:
            print(f"[Dummy] local_job.sh exited with error code {process.returncode}")

    except Exception as e:
        print(f"[Dummy] Exception while running local_job.sh: {e}")

    # Job finished, reset the job_running flag
    with job_lock:
        global is_splat_gen
        try: 
            shutil.copy2("../splat_workspace/result_data/splat.ply", DOWNLOAD_FOLDER)
            is_splat_gen = True
            job_running = False
        except:
            is_splat_gen = False
            job_running = False
            
        
    
@app.route('/status', methods=['GET'])
def job_status():
    """Returns whether a job is currently running."""
    with job_lock:
        if job_running:
            return {"status": "running"}, 200
        else:
            if is_splat_gen:
                CallViewerDummy.main()   # Hier das andere scrip 
                return {"status": "idle_succes"}, 200
            else:
                return {"status": "idle_fail"}, 200

@app.route('/upload', methods=['POST'])
def upload_video():
    """
    Endpoint to upload a video file and start a job to process it.
    Rejects new jobs if one is already running.
    """

    global job_running

    with job_lock:
        if job_running:
            return "A job is already running. Please wait.", 429
        job_running = True

    # Validate file presence
    if 'video' not in request.files:
        with job_lock:
            job_running = False
        return "No video file found in request.", 400

    video = request.files['video']
    if video.filename == '':
        with job_lock:
            job_running = False
        return "No file selected.", 400

    clear_directory(UPLOAD_FOLDER)
    clear_directory("../splat_workspace/input_data")
    clear_directory(DOWNLOAD_FOLDER)
    # Save the uploaded file
    save_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(save_path)
    print(f"Video saved: {save_path}")

    # Parse form parameters with defaults and bounds
    iterations = request.form.get('iterations', '').strip() or '10000'
    iterations = int(iterations)
    keep_pre = request.form.get('keep_pre', '').strip() or '100'
    keep_pre = int(keep_pre)
    keep_post = request.form.get('keep_post', '').strip() or '100'
    keep_post = int(keep_post)
    keep_train_images = request.form.get('keep_train_images', '').strip() or '100'
    keep_train_images = int(keep_train_images)

    # Clamp parameter values
    iterations = max(1, iterations)
    keep_pre = max(1, min(keep_pre, 100))
    keep_post = max(1, min(keep_post, 100))
    keep_train_images = max(1, min(keep_train_images, 100))

    print(f"Received parameters: keep_pre={keep_pre}, keep_post={keep_post}, "
          f"keep_train_images={keep_train_images}, iterations={iterations}")

    # Run the job asynchronously to avoid blocking the request
    Thread(
        target=upload_and_monitor_job_dummy,
        args=(save_path, keep_pre, keep_post, keep_train_images, iterations)
    ).start()

    return "Video uploaded and job started.", 200


def start_zrok_tunnel():
    """
    Starts a zrok tunnel subprocess for public access.
    Returns the subprocess handle to allow termination on exit.
    """
    proc = subprocess.Popen(["zrok", "share", "reserved", "--headless", args.url_name])
    print(f"Zrok tunnel started. URL: https://{args.url_name}.share.zrok.io")
    return proc


if __name__ == '__main__':
    # Start the zrok tunnel first
    zrok_process = start_zrok_tunnel()
    try:
        # Start the Flask server on all interfaces, port 8080
        app.run(host='0.0.0.0', port=8080)
    finally:
        # Terminate the zrok tunnel on exit
        zrok_process.terminate()
