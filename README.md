# GSplat Master's Project – Setup Guide

## 🚀 Description

Access the LRZ Cluster Dashboard:
👉 [https://ood-1.ai.lrz.de/pun/sys/dashboard](https://ood-1.ai.lrz.de/pun/sys/dashboard)
To Work with LRZ AI Sytems you need eduVPN and connect with "Münchner Wissenschaftsnetz LRZ-VPN"

This Reository contains a Gaussian Splatting-based 3D reconstruction pipeline designed for efficient and high-quality 3D scene modeling from video or images. The project includes a complete processing pipeline that runs on the LRZ AI cluster or locally with NVIDIA GPUs, and features an Android app (SplatScan) to capture videos, set parameters, and upload data seamlessly for 3D reconstruction.

The pipeline supports multiple input types (video, images, COLMAP data) and outputs high-fidelity 3D models (.ply files) using a modular, configurable workflow optimized for GPU acceleration.

---

## 📦 Project Setup Instructions

### 📁 Clone Repository

```bash
git clone https://github.com/Kiwil23/GSplat_MA_Projekt.git
cd GSplat_MA_Projekt
```

---

### 🐍 Conda Environment

Create and activate the environment:

```bash
conda env create -f environment.yml
conda activate splat_pipeline
```

Or install manually:

```bash
pip install flask paramiko
```

---

### 🌐 Zrok Setup

1. [Install zrok](https://docs.zrok.io/docs/guides/install/)
2. Create an account:

```bash
zrok invite
```

3. Enable your account:

```bash
zrok enable <your_token>
```

4. Reserve a subdomain:

```bash
zrok reserve public localhost:8080 --unique-name <your_subdomain_name>
```

5. You can release a reservation with:

```bash
zrok release <your_subdomain_name>
```

---

### 🖥️ LRZ AI Cluster Setup

1. Edit the file:
   `Pipeline/cluster/splat_workspace/gpu_job.sbatch`
   Update:

```bash
USER_PATH  → your cluster home directory
```

2. Copy `Pipeline/cluster/splat_workspace` to your cluster home directory.
3. Remove `.gitkeep` files from:

```
input_data/
result_data/
```

4. Connect and create enroot container:

```bash
ssh login.ai.lrz.de -l your_username
cd splat_workspace
salloc -p lrz-hgx-h100-94x4 --gres=gpu:1
srun enroot import docker://kiwil23/splat_tools_slim
exit
```

5. Rename the image:

```bash
mv kiwil23+splat_tools_slim.sqsh kiwil23_splat_tools_slim.sqsh
```

---

### 📱 Android App Setup

1. Enable USB Debugging on your device.
2. Install Android Studio and open:

```
SplatScan/
```

3. Run the app on your device.

---

### 🖥️ Local Docker Setup (NVIDIA GPU only)

1. Install Docker and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
2. Pull the Docker image:

```bash
docker pull kiwil23/splat_tools_slim:latest
```

Or build from source:

```bash
GSplat_MA_Projekt/Docker_Splat_Tools
```

3. Edit:
   `Pipeline/local/splat_workspace/local_job.sh`
   Update:

```bash
USER_PATH  → your project save path
```

4. Remove `.gitkeep` files from:

```
input_data/
result_data/
```

---

## 📱 App Usage

1. **Start the API**  
   - For cluster use:  
     ```bash
     cd Pipeline/cluster/API
     python Cluster_API.py --url-name <Your_Zrok_Subdomain_Name> --cluster-path <Cluster_Home_Path>
     ```
   - For local use:  
     ```bash
     cd Pipeline/local/API
     python Local_API.py --url-name <Your_Zrok_Subdomain_Name>
     ```

2. **Launch the SplatScan App**  
   - Tap `SET URL` and enter your Zrok subdomain name.

3. **Capture Video**  
   - Tap `Start Recording` to record your object.  
   - Try to capture as many angles as possible and ensure good lighting and focus.

4. **Set Training Parameters**  
   Tap `SET PARAMETERS` to define training options (default: `100,100,100,10000`):

   | Option                        | Description                                                    |
   |-------------------------------|----------------------------------------------------------------|
   | `--pre_filter_img="30"`       | Keep top 30% sharpest images (plus 5% extra automatic filtering) |
   | `--post_filter_img="60"`      | Keep top 60% after RAFT filtering                             |
   | `--train_img_percentage="90"` | Use 90% of the remaining images for training                  |
   | `--train_iters=XXXX`          | Number of training iterations                                 |

5. **Upload and Wait**  
   - Tap `UPLOAD VIDEO` and wait for training to finish.  
   - The result `.ply` file will be available in:  
     ```
     /API/downloads
     ```



## ▶️ Manual Pipeline Usage

In `gpu_job.sbatch` or ,`local_job.sh` set the desired `--pipeline_type` and settings:

### 🎥 For MP4 videos in /input_data:

| Argument                              | Result                              |
| ------------------------------------- | ---------------------------------------- |
| `--pipeline_type="mp4_to_images"`     | Extracted frames                           |
| `--pipeline_type="mp4_to_colmap"`     | COLMAP data                              |
| `--pipeline_type="mp4_to_transforms"` | Prepared train data for Splatfacto                   |
| `--pipeline_type="mp4_to_splat"`      | (Default) Full pipeline with .ply output |

### 🖼️ For individual Images in /input_data:

| Argument                                 | Result                    |
| ---------------------------------------- | ------------------------------ |
| `--pipeline_type="images_to_colmap"`     | COLMAP data                      |
| `--pipeline_type="images_to_transforms"` | Prepared train data for Splatfacto         |
| `--pipeline_type="images_to_splat"`      | Full pipeline with .ply output |

### 🗃️ From COLMAP Data in /input_data:

**Required Structure:**

```
input_data/
├── images/
├── sparse/
|   └── 0,1,2...
└── database.db
```

| Argument                                 | Description                    |
| ---------------------------------------- | ------------------------------ |
| `--pipeline_type="colmap_to_transforms"` | Prepared train data for Splatfacto         |
| `--pipeline_type="colmap_to_splat"`      | Full pipeline with .ply output |

### 🗂️ From Preprocessed COLMAP Data:

**Required Structure:**

```
input_data/
├── colmap/
│   ├── sparse/
│   └── database.db
├── images/
├── images_2/
├── images_4/
├── images_8/
├── sparse_pc/
└── transforms.json
```

| Argument                                | Result                    |
| --------------------------------------- | ------------------------------ |
| `--pipeline_type="transforms_to_splat"` | Full pipeline with .ply output |

### 🧹 Optional Image Filtering:

| Option                        | Description                                            |
| ----------------------------- | ------------------------------------------------------ |
| `--pre_filter_img="30"`       | e.g. Keep top 30% sharpest images (plus 5% extra filtering) |
| `--post_filter_img="60"`      | e.g. Keep top 60% after RAFT filtering                      |
| `--train_img_percentage="90"` | e.g. Use 90% of remaining images for training               |
| `--train_iters=XXXX`          | e.g. Number of training iterations                          |

### 🔁 Start Pipeline:

```bash
sbatch gpu_job.sbatch or ./local_job.sh
```

---

## ⚠️ Troubleshooting

**Issue:**

```bash
sbatch: error: Batch script contains DOS line breaks (\r\n)
sbatch: error: instead of expected UNIX line breaks (\n).
```

**Fix:**

```bash
sed -i 's/\r$//' gpu_job.sbatch
sbatch gpu_job.sbatch
```
