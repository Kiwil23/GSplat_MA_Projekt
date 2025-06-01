#!/bin/bash
# === Werte aus sbatch-Aufruf entgegennehmen ===
PRE_FILTER=${1:-100}
POST_FILTER=${2:-100}
TRAIN_IMG_PERCENTAGE=${3:-100}
TRAIN_ITERS=${4:-10000}

#------------CHANE TO YOUR PATH---------------
USER_PATH=/mnt/c/Users/rohes/Desktop/a/local/splat_workspace
#------------CHANE TO YOUR PATH---------------

docker run --rm -it --gpus all \
  -v $USER_PATH/input_data:/mnt/input_data \
  -v $USER_PATH/result_data:/mnt/result_data \
  -v $USER_PATH/scripts:/mnt/pipeline_scripts \
  -p 7007:7007  \
  splat_tools_slim \
     python3 /mnt/pipeline_scripts/pipeline.py \
    --pipeline_type="mp4_to_splat" \
    --pre_filter_img="$PRE_FILTER" \
    --post_filter_img="$POST_FILTER" \
    --train_img_percentage="$TRAIN_IMG_PERCENTAGE" \
    --train_iters="$TRAIN_ITERS" \
    && echo "pipeline.py done"


