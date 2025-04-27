# GSplat_MA_Projekt

## Pipeline mit Enroot Container ausführen

### Schritte:

1. Mit SSH verbinden:
```bash
   ssh login.ai.lrz.de -l xxyyyzz
   ```

2. Source Images in `original_iamges` packen
   

3. Den Ordner `Containers` aus `/container_workspace` auf das `/home` Verzeichnis mit SSH SCP Command oder über das Frontend hochladen.


4. Eine interaktive Session starten:
   ```bash
   salloc -p lrz-hgx-h100-94x4 --gres=gpu:1
   ```
   Allocation mit `srun nvidia-smi` überprüfen. Wenn die H100 angezeigt wird, ist alles ok.

5. Docker Image mit Enroot importieren (funktioniert nur auf Computing-Knoten):
   ```bash
   srun enroot import docker://kiwil23/splat_tools_slim
   ```
   Benenne die File zu "kiwil23_splat_tools_slim" um

6. Interaktive Session mit `exit` beenden, um Ressourcen wieder freizugeben.

8. In `gpu_job.sbatch` Pfade anpassen.

9. Batch-Job mit folgendem Befehl starten:
   ```bash
   sbatch gpu_job.sbatch
   ```

10. Falls ein Fehler auftritt:
    ```
    sbatch: error: Batch script contains DOS line breaks (\r\n)
    sbatch: error: instead of expected UNIX line breaks (\n).
    ```

11. Den Fehler beheben mit:
    ```bash
    sed -i 's/\r$//' gpu_job.sbatch
    ```
    Und dann nochmal:
    ```bash
    sbatch gpu_job.sbatch
    ```

12. Der Ordner "scrips" enthält pipeline.py Dieses Script steuert den Ablauf im Container und kann modifiziert werden.
13. In result_data findet sich dann das splat.ply, die Trainingsdaten und das rohe Splatfacto Ergeniss
14. Der Container beinhaltet Colmap, die Nerfacto/Splatfacto Pipeline sowie das Colmap read_write_module.py das mit import read_write_module verwendet werden kann.

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
