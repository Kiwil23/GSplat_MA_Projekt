#!/bin/bash
#SBATCH -p lrz-hgx-h100-94x4
#SBATCH --gres=gpu:1
#SBATCH -o LOG.out
#SBATCH -e ERROR.err

# Instanzname
INSTANCE=splat_tools_instance

# Image-Datei
IMAGE_PATH=/dss/dsshome1/09/di97yuz/Containers/kiwil23_splat_tools_slim.sqsh

# Cleanup bei Exit (auch bei Fehlern)
trap "echo 'Cleaning up Enroot instance...'; enroot remove -f $INSTANCE" EXIT

# Container erstellen, wenn er noch nicht existiert
    enroot create --name $INSTANCE $IMAGE_PATH


# Enroot-Container starten und python-Script ausführen
enroot start \
    --mount /dss/dsshome1/09/di97yuz/Containers/original_images:/mnt/original_images \
    --mount /dss/dsshome1/09/di97yuz/Containers/result_data:/mnt/result_data \
    --mount /dss/dsshome1/09/di97yuz/Containers/scripts:/mnt/pipeline_scripts \
    $INSTANCE \
    python3 /mnt/pipeline_scripts/pipeline.py && echo "pipeline.py done"
