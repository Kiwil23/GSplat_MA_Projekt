import os
import subprocess
import shutil


# Basis-Pipeline-Workspace-Verzeichnis im Container
pipeline_workspace_dir = "/pipeline_workspace"

result_data_dir = "/mnt/result_data"
pipeline_scripts_dir = "/mnt/pipeline_scripts"

# Pfade zu den Unterordnern relativ zum pipeline_workspace_dir
train_data_dir = "/mnt/train_data" 



def echo(msg):
    print(f"\033[92m✔ {msg}\033[0m")  # Grün



# SplatFacto Training starten
echo("SplatFacto: Training gestartet")
subprocess.run([
    "ns-train", "splatfacto-big",
    "--max-num-iterations", "20000",
    "--pipeline.model.cull_alpha_thresh", "0.004",
    "--pipeline.model.cull_scale_thresh", "0.1",
    "--pipeline.model.reset_alpha_every", "10",
    "--pipeline.model.use_scale_regularization", "True",
    "--viewer.websocket-port", "None",
    "--viewer.quit-on-train-completion", "True",
    "--output-dir", result_data_dir,
    "nerfstudio-data",
    "--data", train_data_dir,
    "--downscale-factor", "1",
 
], check=True)
echo("SplatFacto: Training erfolgreich")


# Suche Ordner der config.yml für Export (Ordnername nicht vorhersehbar)
config_Parent_dir = os.path.join(result_data_dir,"unnamed/splatfacto" )  
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

os.rename(os.path.join(result_data_dir,"unnamed"), os.path.join(result_data_dir,"nerfstudio_output_data"))
print("\n\033[94m Pipeline abgeschlossen.\033[0m")