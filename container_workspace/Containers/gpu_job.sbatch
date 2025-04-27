#!/bin/bash
#SBATCH -p lrz-hgx-h100-94x4
#SBATCH --gres=gpu:1
#SBATCH -o LOG.out
#SBATCH -e ERROR.err

# Instanzname
INSTANCE=splat_tools_instance

# Image-Datei
#Hier <FULL_PATH_TO> durch den vollen Pfad zu der .sqsh Datein einfügen
IMAGE_PATH=<FULL_PATH_TO>/Containers/kiwil23_splat_tools_slim.sqsh

# Cleanup bei Exit (auch bei Fehlern)
trap "echo 'Cleaning up Enroot instance...'; enroot remove -f $INSTANCE" EXIT

# Container erstellen, wenn er noch nicht existiert
    enroot create --name $INSTANCE $IMAGE_PATH


# Enroot-Container starten und python-Script ausführen
#Hier <FULL_PATH_TO> durch den vollen Pfad zu "original_images" , "result_data" , "scrips" Ordnern einfügen
enroot start \
    --mount <FULL_PATH_TO>/Containers/original_images:/mnt/original_images \
    --mount <FULL_PATH_TO>/Containers/result_data:/mnt/result_data \
    --mount <FULL_PATH_TO>/Containers/scripts:/mnt/pipeline_scripts \
    $INSTANCE \
    python3 /mnt/pipeline_scripts/pipeline.py && echo "pipeline.py done"
