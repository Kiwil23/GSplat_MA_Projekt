import os
import subprocess
import sys
import getpass
import shutil
import time
from flask import Flask, request, send_file, abort
import paramiko
import argparse
from threading import Thread, Lock
import re
import posixpath
import CallViewerDummy

app = Flask(__name__)

# Local folders
UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'downloads'
CLUSTER_PATH = '/dss/dsshome1/09/di97yuz'
URL_NAME = 'splatscan777scapp777'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Argument parsing
parser = argparse.ArgumentParser(description="Flask upload server with cluster integration")
parser.add_argument("--cluster-path", default=CLUSTER_PATH, help="Destination path on the cluster for uploaded video")
parser.add_argument("--url-name", default=URL_NAME, help="Name of your reserved zrok URL")
args = parser.parse_args()

cluster_path = args.cluster_path
vid_path = posixpath.join(cluster_path,"splat_workspace/input_data/Source_Video.mp4")
out_path = posixpath.join(cluster_path,"splat_workspace/result_data")
job_path = posixpath.join(cluster_path,"splat_workspace/gpu_job.sbatch")

# SSH login
REMOTE_HOST = "login.ai.lrz.de"
username = input("Enter your cluster username: ")
password = getpass.getpass("Enter your cluster password: ")

# Job control variables
job_running = False
job_lock = Lock()

is_splat_gen = False

def clear_directory(directory_path):
    """Remove all files and folders from the given directory."""
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

def is_job_running(ssh, job_id):
    """Check if a SLURM job with job_id is still running."""
    stdin, stdout, stderr = ssh.exec_command(f"squeue -j {job_id}")
    output = stdout.read().decode()
    return job_id in output

def download_file_from_cluster(ssh, remote_path, local_path):
    """Download a file from the cluster via SFTP."""
    sftp = ssh.open_sftp()
    sftp.get(remote_path, local_path)
    sftp.close()

def print_progress(transferred, total):
    percent = (transferred / total) * 100
    print(f"Upload progress: {percent:.2f}% ({transferred}/{total} bytes)", end='\r')


def upload_and_monitor_job(save_path, keep_pre, keep_post, keep_train_img, iterations):
    """Handles upload, job submission, monitoring, and downloading result file."""

    global job_running
    ssh = None

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, username=username, password=password)

        # Upload video to cluster
        sftp = ssh.open_sftp()
        print(f"Starting upload of {save_path} to {vid_path} ...")
        sftp.put(save_path, vid_path, callback=print_progress)
        print("\nUpload finished.")
        sftp.close()
        print(f"Uploaded video to cluster at {vid_path}")

        # Submit SLURM job and get job ID
        stdin, stdout, stderr = ssh.exec_command(f"sbatch {job_path} {keep_pre} {keep_post} {keep_train_img} {iterations}")
        output = stdout.read().decode()
        error = stderr.read().decode()

        if error:
            print(f"Error submitting job: {error}")
            job_running = False
            return

        print(f"Job submission output: {output}")

        # Extract job ID from sbatch output
        match = re.search(r"Submitted batch job (\d+)", output)
        if not match:
            print("Failed to get job ID from sbatch output.")
            job_running = False
            return

        job_id = match.group(1)
        print(f"Monitoring job ID: {job_id}")

        # Poll job status until finished
        while True:
            time.sleep(10)  # Wait 10 seconds between checks
            if not is_job_running(ssh, job_id):
                print(f"Job {job_id} finished.")
                break
            else:
                print(f"Job {job_id} still running...")

        # Download .ply result file from cluster
        remote_ply_path = posixpath.join(out_path, "splat.ply")
        local_ply_path = os.path.join(DOWNLOAD_FOLDER, "splat.ply")

        try:
            global is_splat_gen
            download_file_from_cluster(ssh, remote_ply_path, local_ply_path)
            print(f"Downloaded output file to {local_ply_path}")
            is_splat_gen = True
        except Exception as e:
            print(f"Failed to download output file: {e} searched remote in {remote_ply_path} {local_ply_path}")
            is_splat_gen = False

    except Exception as e:
        print(f"Exception in upload_and_monitor_job: {e}")
    finally:
        if ssh:
            ssh.close()
        with job_lock:
            job_running = False


def safe_int(value, default):
    """
    Convert a string to int safely, returning default if input is empty or invalid.
    """
    try:
        if value is None or value.strip() == '':
            return default
        return int(value)
    except ValueError:
        return default

@app.route('/status', methods=['GET'])
def job_status():
    """Returns whether a job is currently running."""
    with job_lock:
        if job_running:
            return {"status": "running"}, 200
        else:
            if is_splat_gen:
                CallViewerDummy.main() # Hier das andere scrip
                return {"status": "idle_succes"}, 200
            else:
                return {"status": "idle_fail"}, 200

@app.route('/upload', methods=['POST'])
def upload_video():
    """Upload endpoint: accepts a video and starts a cluster job if idle."""
    
    global job_running

    with job_lock:
        if job_running:
            return "A job is already running. Please wait until it finishes.", 429
        job_running = True

    if 'video' not in request.files:
        with job_lock:
            job_running = False
        return "No video file part in the request.", 400

    video = request.files['video']
    if video.filename == '':
        with job_lock:
            job_running = False
        return "No selected file.", 400
    
    clear_directory(UPLOAD_FOLDER)
    clear_directory(DOWNLOAD_FOLDER)
    save_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(save_path)
    print(f"Video saved to: {save_path}")

    # Parameter aus dem Formular auslesen (Default-Werte falls nicht gesetzt)
    iterations = request.form.get('iterations', '').strip() or '10000'
    iterations = int(iterations)
    keep_pre = request.form.get('keep_pre', '').strip() or '100'
    keep_pre = int(keep_pre)
    keep_post = request.form.get('keep_post', '').strip() or '100'
    keep_post = int(keep_post)
    keep_train_images = request.form.get('keep_train_images', '').strip() or '100'
    keep_train_images = int(keep_train_images)

    iterations = max(1, iterations)
    keep_pre = max(1, min(keep_pre, 100))
    keep_post = max(1, min(keep_post, 100))
    keep_train_images = max(1, min(keep_train_images, 100))

    print(f"Received parameters: keep_pre={keep_pre}, keep_post={keep_post}, images={keep_train_images} iterations={iterations}")

    Thread(target=upload_and_monitor_job, args=(save_path,keep_pre,keep_post,keep_train_images,iterations)).start()

    return "Video uploaded and job started successfully.", 200

@app.route('/download/<filename>', methods=['GET'])
def download_ply(filename):
    """Download endpoint: serves .ply files from the local download folder."""
    if not filename.endswith(".ply"):
        return "Only .ply files are allowed.", 400

    local_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(local_path):
        return abort(404, description="Requested file not found. It may not be generated yet.")

    return send_file(local_path, as_attachment=True)

def start_zrok_tunnel():
    """Start a zrok tunnel for public access."""
    proc = subprocess.Popen(["zrok", "share", "reserved", "--headless", args.url_name])
    print(f"zrok tunnel started. URL: https://{args.url_name}.share.zrok.io")
    return proc

if __name__ == '__main__':
    zrok_process = start_zrok_tunnel()
    try:
        app.run(host='0.0.0.0', port=8080)
    finally:
        zrok_process.terminate()
