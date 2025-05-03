# GSplat_MA_Projekt

## Pipeline auf Cluster ausführen

### Enroot Container Clonen:

Frontend öffnen https://ood-1.ai.lrz.de/pun/sys/dashboard

3. Einen Ordner `Containers` im `/home` Verzeichnis erstellen

1. Mit SSH verbinden:
```bash
   ssh login.ai.lrz.de -l xxyyyzz
   ```
und    ```cd Containers   ``` Verzeichnis wechseln

4. Eine interaktive Session starten:
   ```bash
   salloc -p lrz-hgx-h100-94x4 --gres=gpu:1
   ```  
   Allocation mit `srun nvidia-smi` überprüfen. Wenn die H100 angezeigt wird, ist alles ok.  

5. Docker Image mit Enroot importieren (funktioniert nur auf Computing-Knoten):
   ```bash
   srun enroot import docker://kiwil23/splat_tools_slim
   ```
6. Interaktive Session mit `exit` beenden, um Ressourcen wieder freizugeben.
7. Benenne die File zu `kiwil23_splat_tools_slim.sqsh` um

### Pipeline Umgebung vorbereiten:
Folgende struktur anlegen

Jobs
Containers  
│  
├── input_data  
│  
├── result_data  
│  
└── scripts

in scripts alles scripts aus pipeline_assets/main_pipeline/scripts kopieren

in Jobs gpu_job.sbatch packen
pfade in gpu_job.sbatch anpassen

### Pipeline ausführen:
In gpu_job.sbatch können die Argumente --pipeline_type, --is_big_dataset gesetzt werden

Nimmt eine .mp4 in input_data
--pipeline_type = "mp4_to_images" //gibt extrahierte einzelframes zurück
--pipeline_type = "mp4_to_colmap" //gibt colmap Ergenisse zurück
--pipeline_type = "mp4_to_transforms" //gibt für splatfacto vorbereitete colmap Ergebnisse zurück
--pipeline_type = "mp4_to_splat" //gibt alle zum training verwendeten Daten und eine .ply zurück

Nimmt mehrere einzelbilder in input_data
--pipeline_type = "images_to_colmap" //gibt colmap Ergenisse zurück
--pipeline_type = "images_to_transforms" //gibt für splatfacto vorbereitete colmap Ergebnisse zurück
--pipeline_type = "images_to_splat" //gibt alle zum training verwendeten Daten und eine .ply zurück

Nimmt colmap daten in der Form
input_data 
│  
├── images 
│  
├── sparse 
│  
└── database.db

--pipeline_type = "colmap_to_transforms" //gibt für splatfacto vorbereitete colmap Ergebnisse zurück
--pipeline_type = "colmap_to_splat" //gibt alle zum training verwendeten Daten und eine .ply zurück

Nimmt für splatfacto vorbereitete colmap in form von
input_data 
│  
├── colmap
|         ├── sparse
|         ├── database.db
|
├── images 
├── images_2
├── images_4
├── images_8
├── sparse_pc 
│  
└── transforms.json

--pipeline_type = "transforms_to_splat" //gibt alle zum training verwendeten Daten und eine .ply zurück




9. In `gpu_job.sbatch` Pfade anpassen und auf home Verzeichnis im Cluster laden.  

10. Batch-Job mit folgendem Befehl starten:
   ```bash
   sbatch gpu_job.sbatch
   ```  

11. Falls ein Fehler auftritt:
    ```
    sbatch: error: Batch script contains DOS line breaks (\r\n)
    sbatch: error: instead of expected UNIX line breaks (\n).
    ```  

12. Den Fehler beheben mit:
    ```bash
    sed -i 's/\r$//' gpu_job.sbatch
    ```
    Und dann nochmal:
    ```bash
    sbatch gpu_job.sbatch
    ```  

13. Der Ordner "scrips" enthält pipeline.py Dieses Script steuert den Ablauf im Container und kann modifiziert werden.  
14. In result_data findet sich dann das splat.ply, die Trainingsdaten und das rohe Splatfacto Ergeniss  
15. Der Container beinhaltet Colmap, die Nerfacto/Splatfacto Pipeline sowie das Colmap read_write_module.py das mit import read_write_module verwendet werden kann.  

## Lokale Ausführung
### Schritte:
1. Für Windows Docker Desktop herunterladen https://www.docker.com/products/docker-desktop/ (Nutzung von WSL 2 sicherstellen, evtl. müssen Host Resourcen mit einer wsl.config erweitert werden)  
2. Für Linux https://docs.docker.com/engine/install/ubuntu/  
3. NVIDIA Container Toolkit instalieren https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html  
4. Verzeichnis anlegen mit der Struktur:  
MeinVerzeichnis  
│  
├── original_images  
│  
├── result_data  
│  
└── scripts  

5. `pipeline.py` in `scripts` kopieren und source Bilder in `original_images` packen
   
6. `cd <FULL_PATH_TO>/Docker`  
7. `docker build -t <IMAGE_NAME> .`  
8. `docker run -it --gpus all -v <FULL_PATH_TO>/original_images:/mnt/original_images -v <FULL_PATH_TO>/result_data:/mnt/result_data -v <FULL_PATH_TO>/scripts:/mnt/pipeline_scrips -p 7007:7007 <IMAGE_NAME> python3 /mnt/pipeline_scrips/pipeline.py  `  
9. In `result_data` findet sich dann das `splat.ply`, die Trainingsdaten und das rohe Splatfacto Ergeniss

## Image auf DockerHub
 https://hub.docker.com/repository/docker/kiwil23/splat_tools_slim/general
