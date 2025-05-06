import os
import subprocess
import shutil
import argparse
import json

# ---------------------------------------------------------------------------------------------------------------------------
# Prepare ArgumentParser to determine the pipeline type and filter options from command-line arguments
# ---------------------------------------------------------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--pipeline_type", default="mp4_to_splat")
parser.add_argument("--pre_filter_img", type=float, nargs='?', const=True, default=False)
parser.add_argument("--train_img_percentage", type=float, nargs='?', const=True, default=False)
parser.add_argument("--post_filter_img", type=float, nargs='?', const=True, default=False)

args = parser.parse_args()

pipeline_type = args.pipeline_type

# pre_filter_img can be False (not set), True (only flag passed), or float
if args.pre_filter_img is False:
    pre_filter_img = False
elif args.pre_filter_img is True:
    print("Please provide a numerical value for --pre_filter_img, e.g., 80.0")
    exit(1)
else:
    pre_filter_img = args.pre_filter_img / 100.0

# train_img_percentage can be False (not set), True (only flag passed), or float
if args.train_img_percentage is False:
    train_img_percentage = False
elif args.train_img_percentage is True:
    print("Please provide a numerical value for --train_img_percentage, e.g., 80.0")
    exit(1)
else:
    train_img_percentage = args.train_img_percentage / 100.0

# post_filter_img can be False (not set), True (only flag passed), or float
if args.post_filter_img is False:
    post_filter_img = False
elif args.post_filter_img is True:
    print("Please provide a numerical value for --post_filter_img, e.g., 80.0")
    exit(1)
else:
    post_filter_img = args.post_filter_img / 100.0

# ---------------------------------------------------------------------------------------------------------------------------
# Utility function for deleting directory contents
# ---------------------------------------------------------------------------------------------------------------------------
def clear_directory(directory_path):
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
    else:
        print(f"Directory {directory_path} does not exist.")

# ---------------------------------------------------------------------------------------------------------------------------
# Prepare container workspace
# ---------------------------------------------------------------------------------------------------------------------------
pipeline_workspace_dir = "/pipeline_workspace"
input_data_dir = "/mnt/input_data"
result_data_dir = "/mnt/result_data"
pipeline_scripts_dir = "/mnt/pipeline_scripts"

clear_directory(result_data_dir)

train_data_dir = os.path.join(pipeline_workspace_dir, "train_data")
extracted_images_dir = os.path.join(train_data_dir, "extracted_images")
colmap_data_dir = os.path.join(train_data_dir, "colmap")
db_path = os.path.join(colmap_data_dir, "database.db")
sparse_dir = os.path.join(colmap_data_dir, "sparse")

os.makedirs(train_data_dir, exist_ok=True)
os.makedirs(extracted_images_dir, exist_ok=True)
os.makedirs(colmap_data_dir, exist_ok=True)
os.makedirs(sparse_dir, exist_ok=True)

def echo(msg):
    print(f"\033[92m✔ {msg}\033[0m")

# ---------------------------------------------------------------------------------------------------------------------------
# Extract sharp and clear images from an mp4 file, ensuring good overlap between frames while keeping the overall image count relatively low.
# ---------------------------------------------------------------------------------------------------------------------------
def extract_useful_images(in_dir, out_dir):
    temp_input_dir = ""
    
    # Pre-cleanup of blurry images and reduces count of images (
    if isinstance(pre_filter_img, float):       
        # Decides if input is a video or multiple images
        if len(os.listdir(in_dir)) > 1:
            input = in_dir
        else:
            input = os.path.join(in_dir, os.listdir(in_dir)[0])

        echo(f"\033[92mRemoving the worst 5% of images.\033[0m")
        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "01_filter_raw_data.py"),
            "--input_path", input,
            "--output_path", out_dir,
            "--target_percentage", "95",
            "--groups", "1",
            "--yes"
        ], check=True)
        print(f"\033[92mFiltered to {len(os.listdir(out_dir))} images.\033[0m")

        echo(f"\033[92mFiltering to retain top {pre_filter_img * 100}% sharpest images\033[0m")
        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "01_filter_raw_data.py"),
            "--input_path", out_dir,
            "--output_path", out_dir,
            "--target_count", str(int(len(os.listdir(out_dir)) * pre_filter_img)),
            "--scalar", "3",
            "--yes"
        ], check=True)
        print(f"\033[92mFiltered to {len(os.listdir(out_dir))} images.\033[0m")
        temp_input_dir = "/temp_input"
        shutil.copytree(out_dir, temp_input_dir)
        
    else:
        temp_input_dir = os.path.join(in_dir, os.listdir(in_dir)[0])

    echo("Starting image selection...")  
    clear_directory(out_dir)
    subprocess.run([
        "python3", os.path.join(pipeline_scripts_dir, "raft_extractor.py"),
        "--in", temp_input_dir,
        "--out", out_dir,
        "--motion_threshold", "50",
        "--sharpness_threshold", "10",
        "--exposure_threshold", "240"
    ], check=True)    
    if isinstance(pre_filter_img, float):
        shutil.rmtree(temp_input_dir)          
    print(f"\033[92mSelected {len(os.listdir(out_dir))} images.\033[0m")

    # Extra cleanup of blurry images and reduces count of images
    if isinstance(post_filter_img, float):
        echo(f"\033[92mFiltering to retain top {post_filter_img * 100}% sharpest images\033[0m")
        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "01_filter_raw_data.py"),
            "--input_path", out_dir,
            "--target_count", str(int(len(os.listdir(out_dir)) * post_filter_img)),
            "--scalar", "1",
            "--yes"
        ], check=True)
        print(f"\033[92mFiltered to {len(os.listdir(out_dir))} images.\033[0m")

# ---------------------------------------------------------------------------------------------------------------------------
# Run COLMAP to reconstruct sparse 3D structure from images
# ---------------------------------------------------------------------------------------------------------------------------
def run_colmap_pipeline(in_dir, database):
    # Step 1: Create database
    subprocess.run(["colmap", "database_creator", "--database_path", database], check=True)
    echo("COLMAP: Database created.")

    # Step 2: Feature extraction
    subprocess.run([
        "colmap", "feature_extractor",
        "--database_path", database,
        "--image_path", in_dir,
        "--SiftExtraction.use_gpu", "1",
        "--SiftExtraction.gpu_index", "0",
        "--SiftExtraction.max_image_size", "2400",
        "--SiftExtraction.max_num_features", "8192",
        "--SiftExtraction.peak_threshold", "0.006666666666666667",
        "--SiftExtraction.edge_threshold", "10",
        "--ImageReader.single_camera", "1",
        "--ImageReader.camera_model", "SIMPLE_RADIAL"
    ], check=True)
    echo("COLMAP: Feature extraction completed.")

    # Step 3: Feature matching
    subprocess.run([
        "colmap", "exhaustive_matcher",
        "--database_path", database,
        "--SiftMatching.use_gpu", "1",
        "--SiftMatching.gpu_index", "0",
        "--SiftMatching.max_ratio", "0.6",
        "--SiftMatching.cross_check", "1",
        "--SiftMatching.guided_matching", "1"
    ], check=True)
    echo("COLMAP: Feature matching completed.")

    # Step 4: Mapping
    subprocess.run([
        "colmap", "mapper",
        "--database_path", database,
        "--image_path", in_dir,
        "--output_path", sparse_dir,
        "--Mapper.num_threads", "40",
        "--Mapper.abs_pose_min_num_inliers", "15",
        "--Mapper.abs_pose_min_inlier_ratio", "0.15",
        "--Mapper.tri_min_angle", "2.5",
        "--Mapper.init_min_num_inliers", "100",
        "--Mapper.init_num_trials", "200",
        "--Mapper.ba_global_max_num_iterations", "60", # Changed from 75
        "--Mapper.ba_global_max_refinements", "1", # Changed from 5
        "--Mapper.ba_global_max_refinement_change", "0.0005",
        "--Mapper.extract_colors", "1",
        "--Mapper.fix_existing_images", "0",
        "--Mapper.tri_ignore_two_view_tracks", "1",
        "--Mapper.min_num_matches", "15"
    ], check=True)
    echo("COLMAP: Mapping completed.")

# ---------------------------------------------------------------------------------------------------------------------------
# Prepare training data and transforms.json for SplatFacto
# ---------------------------------------------------------------------------------------------------------------------------
def prepare_colmap_data_for_splatfacto(in_dir, out_dir, colmap_dir):
    echo("Preparing training data for SplatFacto...")
    subprocess.run([
        "ns-process-data", "images",
        "--skip-colmap",
        "--colmap-model-path", colmap_dir,
        "--data", in_dir,
        "--output_dir", out_dir
    ], check=True)

    # Choose a smaller image amount for training but can fail on small datasets
    if isinstance(train_img_percentage, float):
        echo("Filtering images for training...")
        transforms_path = os.path.join(train_data_dir, "transforms.json")
        
        with open(transforms_path, "r") as f:
            data = json.load(f)
        
        frames = data.get("frames", [])
        print(f"\033Registered images: {len(frames)}\033")

        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "02_filter_colmap_data.py"),
            "--transforms_path", transforms_path,
            "--target_count", str(int(len(frames) * train_img_percentage)),
            "--yes"
        ], check=True)

        # Replace transforms.json with the filtered one
        original = transforms_path
        filtered = os.path.join(train_data_dir, "transforms_filtered.json")

        if os.path.exists(original):
            os.remove(original)
        os.rename(filtered, original)

# ---------------------------------------------------------------------------------------------------------------------------
# Copy train data to host for debugging and cleanup extracted images
# ---------------------------------------------------------------------------------------------------------------------------
def write_result_data():
    shutil.copytree(train_data_dir, os.path.join(result_data_dir, "train_data_copy"))
    echo(f"Training data copied to {os.path.join(result_data_dir, 'train_data_copy')}")

# ---------------------------------------------------------------------------------------------------------------------------
# Train SplatFacto using prepared transforms
# ---------------------------------------------------------------------------------------------------------------------------
def run_splatfacto(in_dir):
    echo("Starting SplatFacto training...")
    subprocess.run([
        "ns-train", "splatfacto",
        "--max-num-iterations", "15000",
        "--pipeline.model.cull_alpha_thresh", "0.05",
        "--pipeline.model.stop_screen_size_at", "4000",
        "--pipeline.model.cull_scale_thresh", "0.2",
        "--pipeline.model.reset_alpha_every", "50",
        "--pipeline.model.use_scale_regularization", "True",
        "--viewer.quit-on-train-completion", "True",
        "--output-dir", result_data_dir,
        "nerfstudio-data",
        "--data", in_dir,
        "--downscale-factor", "1"
    ], check=True)
    echo("SplatFacto training completed.")

# ---------------------------------------------------------------------------------------------------------------------------
# Export Gaussian Splat as .ply
# ---------------------------------------------------------------------------------------------------------------------------
def export_ply():
    config_parent_dir = os.path.join(result_data_dir, "unnamed/splatfacto")
    folders = [f for f in os.listdir(config_parent_dir) if os.path.isdir(os.path.join(config_parent_dir, f))]

    if folders:
        folder = folders[0]
        config_file_path = os.path.join(config_parent_dir, folder, "config.yml")
        echo(f"Found config: {config_file_path}")
    else:
        print("Error: No config folder found.")
        return

    echo("Exporting .ply file...")
    subprocess.run([
        "ns-export", "gaussian-splat",
        "--load-config", config_file_path,
        "--output-dir", result_data_dir
    ], check=True)
    echo("Export completed.")

    os.rename(os.path.join(result_data_dir, "unnamed"), os.path.join(result_data_dir, "nerfstudio_output_data"))

# ---------------------------------------------------------------------------------------------------------------------------
# Execute pipeline based on desired input and result
# ---------------------------------------------------------------------------------------------------------------------------
print(f"\033[92mStarting pipeline: {pipeline_type} with pre_filter_img set to: {pre_filter_img * 100} and post_filter_img set to: {post_filter_img * 100} and train_img_percentage set to: {train_img_percentage * 100}\033[0m")

try:
    if pipeline_type == "preprocces_images":
        extract_useful_images(input_data_dir, extracted_images_dir)
        write_result_data()

    elif pipeline_type == "mp4_to_images":
        extract_useful_images(input_data_dir, extracted_images_dir)
        write_result_data()

    elif pipeline_type == "mp4_to_colmap":
        extract_useful_images(input_data_dir, extracted_images_dir)
        run_colmap_pipeline(extracted_images_dir, db_path)
        write_result_data()

    elif pipeline_type == "mp4_to_transforms":
        extract_useful_images(input_data_dir, extracted_images_dir)
        run_colmap_pipeline(extracted_images_dir, db_path)
        prepare_colmap_data_for_splatfacto(extracted_images_dir, train_data_dir, os.path.join(sparse_dir, "0"))
        write_result_data()

    elif pipeline_type == "mp4_to_splat":
        extract_useful_images(input_data_dir, extracted_images_dir)
        run_colmap_pipeline(extracted_images_dir, db_path)
        prepare_colmap_data_for_splatfacto(extracted_images_dir, train_data_dir, os.path.join(sparse_dir, "0"))
        write_result_data()
        run_splatfacto(train_data_dir)
        export_ply()

    elif pipeline_type == "images_to_colmap":
        run_colmap_pipeline(input_data_dir, db_path)
        write_result_data()

    elif pipeline_type == "images_to_transforms":
        run_colmap_pipeline(input_data_dir, db_path)
        prepare_colmap_data_for_splatfacto(input_data_dir, train_data_dir, os.path.join(sparse_dir, "0"))
        write_result_data()

    elif pipeline_type == "images_to_splat":
        run_colmap_pipeline(input_data_dir, db_path)
        prepare_colmap_data_for_splatfacto(input_data_dir, train_data_dir, os.path.join(sparse_dir, "0"))
        write_result_data()
        run_splatfacto(train_data_dir)
        export_ply()

    elif pipeline_type == "colmap_to_transforms":
        prepare_colmap_data_for_splatfacto(os.path.join(input_data_dir, "images"), train_data_dir, os.path.join(input_data_dir, "sparse/0"))
        write_result_data()

    elif pipeline_type == "colmap_to_splat":
        prepare_colmap_data_for_splatfacto(os.path.join(input_data_dir, "images"), train_data_dir, os.path.join(input_data_dir, "sparse/0"))
        write_result_data()
        run_splatfacto(train_data_dir)
        export_ply()

    elif pipeline_type == "transforms_to_splat":
        run_splatfacto(input_data_dir)
        export_ply()

except subprocess.CalledProcessError as e:
    print(f"\n\033[91mPipeline failed: {e}\033[0m")
    write_result_data()

# ---------------------------------------------------------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------------------------------------------------------
print("\n\033[94mPipeline completed.\033[0m")