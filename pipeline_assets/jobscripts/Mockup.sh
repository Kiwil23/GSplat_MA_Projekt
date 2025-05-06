#!/bin/bash

docker run -it --gpus all \
  -v <PATH_TO>/input_data:/mnt/input_data \
  -v <PATH_TO>/result_data:/mnt/result_data \
  -v <PATH_TO>/scripts:/mnt/pipeline_scripts \
  -p 7007:7007  \
  splat_tools_slim \
  python3 /mnt/pipeline_scripts/pipeline.py \
  --pipeline_type="mp4_to_splat" \
  --pre_filter_img="50" \
  --post_filter_img="50" \
  --train_img_percentage="50" \
  && echo "pipeline.py done"


