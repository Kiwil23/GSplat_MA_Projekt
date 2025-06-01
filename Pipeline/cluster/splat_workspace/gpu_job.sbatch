#!/bin/bash
#SBATCH -p lrz-hgx-h100-94x4
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00   
#SBATCH -o splat_workspace/LOG.out
#SBATCH --cpus-per-task=40

# === Werte aus sbatch-Aufruf entgegennehmen ===
PRE_FILTER=${1:-100}
POST_FILTER=${2:-100}
TRAIN_IMG_PERCENTAGE=${3:-100}
TRAIN_ITERS=${4:-10000}

#------------CHANE TO YOUR PATH---------------
USER_PATH=/dss/dsshome1/09/di97yuz
#------------CHANE TO YOUR PATH---------------

# Instanzname
INSTANCE=splat_tools_instance
# Image-Datei
IMAGE_PATH=$USER_PATH/splat_workspace/kiwil23_splat_tools_slim.sqsh

# Cleanup bei Exit (auch bei Fehlern)
trap "echo 'Cleaning up Enroot instance...'; enroot remove -f $INSTANCE" EXIT

# Container erstellen, wenn er noch nicht existiert
    enroot create --name $INSTANCE $IMAGE_PATH

# Enroot-Container starten und python-Script ausführen
enroot start \
    --mount $USER_PATH/splat_workspace/input_data:/mnt/input_data \
    --mount $USER_PATH/splat_workspace/result_data:/mnt/result_data \
    --mount $USER_PATH/splat_workspace/scripts:/mnt/pipeline_scripts \
    $INSTANCE \
     python3 /mnt/pipeline_scripts/pipeline.py \
    --pipeline_type="mp4_to_splat" \
    --pre_filter_img="$PRE_FILTER" \
    --post_filter_img="$POST_FILTER" \
    --train_img_percentage="$TRAIN_IMG_PERCENTAGE" \
    --train_iters="$TRAIN_ITERS" \
    && echo "pipeline.py done"