#!/bin/bash

docker run -it --gpus all \
  -v /mnt/c/Users/rohes/Desktop/PipelineTest/input_data:/mnt/input_data \
  -v /mnt/c/Users/rohes/Desktop/PipelineTest/result_data:/mnt/result_data \
  -v /mnt/c/Users/rohes/Desktop/PipelineTest/scripts:/mnt/pipeline_scripts \
  -p 7007:7007  \
  splat_tools_slim \
  python3 /mnt/pipeline_scripts/pipeline.py \
  --pipeline_type="mp4_to_splat" \
  --is_big_dataset="True" && echo "pipeline.py done"


