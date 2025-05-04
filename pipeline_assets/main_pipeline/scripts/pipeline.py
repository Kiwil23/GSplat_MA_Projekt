import os
import subprocess
import shutil
import argparse

#---------------------------------------------------------------------------------------------------------------------------
# Prepare ArgumentParser to determine the pipeline type and video characteristics from command-line arguments
#---------------------------------------------------------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--pipeline_type", default="mp4_to_splat")
parser.add_argument("--is_big_dataset", default="False")
args = parser.parse_args()

pipeline_type = args.pipeline_type
is_big_dataset = args.is_big_dataset.lower() == "true"


#---------------------------------------------------------------------------------------------------------------------------
# Function for deleting result_data directory contents on start
#---------------------------------------------------------------------------------------------------------------------------
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


#---------------------------------------------------------------------------------------------------------------------------
# Prepare container workspace
#---------------------------------------------------------------------------------------------------------------------------

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


#---------------------------------------------------------------------------------------------------------------------------
# Extract sharp and clear images from an mp4 file, ensuring good overlap between frames 
# while keeping the overall image count relatively low.
#---------------------------------------------------------------------------------------------------------------------------
def extract_useful_images(in_dir, out_dir):
    echo("Starting image selection...")
    subprocess.run([
        "python3", os.path.join(pipeline_scripts_dir, "raft_extractor.py"),
        "--in", os.path.join(in_dir, os.listdir(in_dir)[0]),
        "--out", out_dir,
        "--motion_threshold", "50",
        "--sharpness_threshold", "10",
        "--exposure_threshold", "240"
    ], check=True)

    print(f"\033[92mSelected {len(os.listdir(out_dir))} images.\033[0m")


    # Does a extra cleanup of blury images but can fail on small datasets
    if is_big_dataset:
        echo("Filtering to retain top 95'%' sharpest images...")
        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "01_filter_raw_data.py"),
            "--input_path", out_dir,
            "--target_percentage", "95",
            "--groups", "1",
            "--yes"
        ], check=True)
        print(f"\033[92mFiltered to {len(os.listdir(out_dir))} images.\033[0m")



#---------------------------------------------------------------------------------------------------------------------------
# Run COLMAP to reconstruct sparse 3D structure from images
#---------------------------------------------------------------------------------------------------------------------------
def run_colmap_pipeline(in_dir, database):
    # Step 1: Create database
    subprocess.run(["colmap", "database_creator", "--database_path", database], check=True)
    echo("COLMAP: Database created.")

    # Step 2: Feature extraction (enhanced)
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

    # Step 3: Feature matching (enhanced)
    subprocess.run([
        "colmap", "exhaustive_matcher",
        "--database_path", database,
        "--SiftMatching.use_gpu", "1",
        "--SiftMatching.gpu_index", "0",
        "--SiftMatching.max_ratio", "0.6",
        "--SiftMatching.cross_check", "1",
        "--SiftMatching.guided_matching", "1",
        #"--SequentialMatching.overlap", "10", # Only for Sequential
        #"--SequentialMatching.quadratic_overlap", "1" # Only for Sequential
    ], check=True)
    echo("COLMAP: Feature matching completed.")

    # Step 4: Mapping (refined)
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
        "--Mapper.ba_global_max_num_iterations", "75",
        "--Mapper.ba_global_max_refinements", "5",
        "--Mapper.ba_global_max_refinement_change", "0.0005",
        "--Mapper.extract_colors", "1",
        "--Mapper.fix_existing_images", "0",
        "--Mapper.tri_ignore_two_view_tracks", "1",
        "--Mapper.min_num_matches", "15"
    ], check=True)
    echo("COLMAP: Mapping completed.")


#---------------------------------------------------------------------------------------------------------------------------
# Prepare training data and transforms.json for SplatFacto
#---------------------------------------------------------------------------------------------------------------------------
def prepare_colmap_data_for_splatfacto(in_dir, out_dir, colmap_dir):
    echo("Preparing training data for SplatFacto...")
    subprocess.run([
        "ns-process-data", "images",
        "--skip-colmap",
        "--colmap-model-path", colmap_dir,
        "--data", in_dir,
        "--output_dir", out_dir
    ], check=True)

    # Choses a smaller image amount for training but can fail on small datasets
    if is_big_dataset:
        img_factor_to_remain = 0.7
        echo("Filtering images for training...")
        subprocess.run([
            "python", os.path.join(pipeline_scripts_dir, "02_filter_colmap_data.py"),
            "--transforms_path", os.path.join(train_data_dir, "transforms.json"),
            "--target_count", str(int(len(os.listdir(os.path.join(train_data_dir, "images"))) * img_factor_to_remain)),
            "--yes"
        ], check=True)

        # Replace transforms.json with the filtered one
        original = os.path.join(train_data_dir, "transforms.json")
        filtered = os.path.join(train_data_dir, "transforms_filtered.json")

        if os.path.exists(original):
            os.remove(original)
        os.rename(filtered, original)

        print(f"\033[92mImages used for training: {int(len(os.listdir(os.path.join(train_data_dir, 'images'))) * img_factor_to_remain)}\033[0m")



#---------------------------------------------------------------------------------------------------------------------------
# Copy train data to host for debugging and cleanup extracted images
#---------------------------------------------------------------------------------------------------------------------------
def write_result_data():
    shutil.copytree(train_data_dir, os.path.join(result_data_dir, "train_data_copy"))
    if os.path.exists(extracted_images_dir):
        shutil.rmtree(extracted_images_dir)
    echo(f"Training data copied to {os.path.join(result_data_dir, 'train_data_copy')}")


#---------------------------------------------------------------------------------------------------------------------------
# Train SplatFacto using prepared transforms
#---------------------------------------------------------------------------------------------------------------------------
def run_splatfacto(in_dir):
    echo("Starting SplatFacto training...")
    subprocess.run([
        "ns-train", "splatfacto",
        "--max-num-iterations", "15000",
        "--pipeline.model.cull_alpha_thresh", "0.05", #Default 0.005
        "--pipeline.model.stop_screen_size_at" ,"4000", #Default 4000
        "--pipeline.model.cull_scale_thresh", "0.2",  #Default 0.5
        "--pipeline.model.reset_alpha_every", "50",  #Default 30
        "--pipeline.model.use_scale_regularization", "True",
        "--viewer.websocket-port", "None",
        "--viewer.quit-on-train-completion", "True",
        "--output-dir", result_data_dir,
        "nerfstudio-data",
        "--data", in_dir,
        "--downscale-factor", "1"
    ], check=True)
    echo("SplatFacto training completed.")


#---------------------------------------------------------------------------------------------------------------------------
# Export Gaussian Splat as .ply
#---------------------------------------------------------------------------------------------------------------------------
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



#---------------------------------------------------------------------------------------------------------------------------
# Execute pipeline based on wished input and result
#---------------------------------------------------------------------------------------------------------------------------
print(f"\033[92mStarting pipeline: {pipeline_type} with is_big_dataset set to: {is_big_dataset}\033[0m")


try:
    if pipeline_type == "mp4_to_images":
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
#---------------------------------------------------------------------------------------------------------------------------
# Done
#---------------------------------------------------------------------------------------------------------------------------
print("\n\033[94mPipeline completed.\033[0m")
