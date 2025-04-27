import os
import subprocess
import shutil


# Basis-Pipeline-Workspace-Verzeichnis im Container
pipeline_workspace_dir = "/pipeline_workspace"

# Pfade zu auf dem Host zugänglichen Ordnern
original_images_dir = "/mnt/original_images"
result_data_dir = "/mnt/result_data"
pipeline_scripts_dir = "/mnt/pipeline_scripts"

# Pfade zu den Unterordnern relativ zum pipeline_workspace_dir
train_data_dir = os.path.join(pipeline_workspace_dir, "train_data")  
images_dir = os.path.join(train_data_dir, "images")  
colmap_data_dir = os.path.join(train_data_dir, "colmap") 
db_path = os.path.join(colmap_data_dir, "database.db") 
sparse_dir = os.path.join(colmap_data_dir, "sparse")  


# Erstelle alle nötigen Verzeichnisse
os.makedirs(train_data_dir, exist_ok=True)
os.makedirs(colmap_data_dir, exist_ok=True)
os.makedirs(sparse_dir, exist_ok=True)

# Kopiere alle Bilder vom Hostordner in das Pipeline Arbeitsverzeichnis (evtl. nicht nötig)
shutil.copytree(original_images_dir, images_dir)


def echo(msg):
    print(f"\033[92m✔ {msg}\033[0m")  # Grün

# Bilder Auswahlscript hier einbinden
# subprocess.run([])

# COLMAP: Database erstellen
subprocess.run(["colmap", "database_creator",
                "--database_path", db_path], check=True)
echo("COLMAP: Datenbank erstellt")

# COLMAP: Feature Extraktion mit GPU-Unterstützung (camera_model muss PINHOLE sein)
subprocess.run([
    "colmap", "feature_extractor",
    "--database_path", db_path,
    "--image_path", images_dir,
    "--SiftExtraction.use_gpu", "1",
    "--SiftExtraction.gpu_index", "0",
    "--ImageReader.single_camera", "1",
    "--ImageReader.camera_model", "PINHOLE"
], check=True)
echo("COLMAP: Feature-Extraktion abgeschlossen (GPU verwendet)")

# COLMAP: Matching mit GPU-Unterstützung
subprocess.run(["colmap", "exhaustive_matcher",
                "--database_path", db_path,
                "--SiftMatching.use_gpu", "1",
                "--SiftMatching.gpu_index", "0"],
               check=True)
echo("COLMAP: Matching abgeschlossen (GPU verwendet)")

# COLMAP: Mapping
subprocess.run(["colmap", "mapper",
                "--database_path", db_path,
                "--image_path", images_dir,
                "--output_path", sparse_dir], check=True)
echo("COLMAP: Mapping abgeschlossen")

# Optional: Pointcloud Bereinigung
# subprocess.run([])

# SplatFacto: Train Data vorbereiten
echo("SplatFacto: Bereite Trainingsdaten vor")
subprocess.run(["ns-process-data", "images",
                "--skip-colmap",
                "--colmap-model-path", os.path.join(sparse_dir, "0"),
                "--data", images_dir,
                "--output_dir", train_data_dir], check=True)
                
# Für Debuging und Überprüfung kopiere die Trainingsdaten auf den Host
shutil.copytree(train_data_dir, os.path.join(result_data_dir, "train_data_copy") )
print(f"Trainingsdaten in {os.path.join(result_data_dir, 'train_data_copy')} kopiert ")
echo("SplatFacto: Trainingsdaten vorbereitet")


# SplatFacto Training starten
echo("SplatFacto: Training gestartet")
subprocess.run(["ns-train", "splatfacto",
                "--viewer.websocket_port", "None",
                "--viewer.quit-on-train-completion", "True",
                "--data", train_data_dir,
                "--output-dir", result_data_dir,
                "--max-num-iterations", "5000"
            ], check=True)
echo("SplatFacto: Training erfolgreich")


# Suche Ordner der config.yml für Export (Ordnername nicht vorhersehbar)
config_Parent_dir = os.path.join(result_data_dir,"train_data/splatfacto" )  
folders = [f for f in os.listdir(config_Parent_dir) if os.path.isdir(os.path.join(config_Parent_dir, f))]

if folders:
    # Nimm den ersten Ordner, da es nur einen gibt
    folder = folders[0]
    print(f"Gefundener Ordner: {folder}")
    
    # Pfad zur Konfigurationsdatei
    config_file_path = os.path.join(config_Parent_dir, folder, "config.yml")
    print(f"Pfad zur Konfigurationsdatei: {config_file_path}")
else:
    print("Kein Ordner gefunden.")

# Export .ply
echo("Export gestartet")
subprocess.run(["ns-export", "gaussian-splat",
                "--load-config", config_file_path,
                "--output-dir", result_data_dir], check=True)
echo("Export abgeschlossen")

os.rename(os.path.join(result_data_dir,"train_data"), os.path.join(result_data_dir,"nerfstudio_output_data"))
print("\n\033[94m Pipeline abgeschlossen.\033[0m")
