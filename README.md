# GSplat_MA_Projekt

## Pipeline auf dem Cluster ausführen

### 📦 Enroot-Container klonen

1. Frontend öffnen:  
   👉 [https://ood-1.ai.lrz.de/pun/sys/dashboard](https://ood-1.ai.lrz.de/pun/sys/dashboard)

2. Einen Ordner `Containers` im `/home`-Verzeichnis anlegen.

3. Mit SSH verbinden:
   ```bash
   ssh login.ai.lrz.de -l xxyyyzz
   cd Containers
   ```

4. Interaktive Session starten:
   ```bash
   salloc -p lrz-hgx-h100-94x4 --gres=gpu:1
   ```

5. Prüfen, ob H100 GPU zugewiesen ist:
   ```bash
   srun nvidia-smi
   ```

6. Docker-Image mit Enroot importieren (**nur auf Compute-Knoten**):
   ```bash
   srun enroot import docker://kiwil23/splat_tools_slim
   ```

7. Session mit `exit` beenden.

8. Datei umbenennen:
   ```bash
   Von kiwil23+splat_tools_slim.sqsh in kiwil23_splat_tools_slim.sqsh
   ```

---

### 🧱 Pipeline-Umgebung vorbereiten

**Verzeichnisstruktur erstellen:**

```
Jobs/
├── gpu_job.sbatch

Containers/
├── input_data/
├── result_data/
└── scripts/
```

- In `Containers/scripts/` (Cluster) alle Dateien aus (Repo) `pipeline_assets/main_pipeline/scripts` kopieren  
- `gpu_job.sbatch` in `Jobs/` speichern und darin die Pfade entsprechend auf die `Containers/`-Struktur anpassen

---

### ▶️ Pipeline ausführen

In `gpu_job.sbatch` können folgende Argumente gesetzt werden:

#### Für .mp4 in `input_data/`:

| Argument                    | Beschreibung                                                  |
|----------------------------|---------------------------------------------------------------|
| `--pipeline_type="mp4_to_images"`            | extrahiert Einzelframes                                       |
| `--pipeline_type="mp4_to_colmap"`            | gibt COLMAP-Ergebnisse zurück                                |
| `--pipeline_type="mp4_to_transforms"`        | COLMAP → für Splatfacto vorbereitet                          |
| `--pipeline_type="mp4_to_splat"`             | (Default) vollständige Pipeline inkl. .ply für Training                |

#### Für Einzelbilder in `input_data/`:

| Argument                    | Beschreibung                                                  |
|----------------------------|---------------------------------------------------------------|
| `--pipeline_type="images_to_colmap"`         | gibt COLMAP-Ergebnisse zurück                                |
| `--pipeline_type="images_to_transforms"`     | COLMAP → für Splatfacto vorbereitet                          |
| `--pipeline_type="images_to_splat"`          | vollständige Pipeline inkl. .ply für Training                |

#### Für vorhandene COLMAP-Daten in ` input_data` :

Ordnerstruktur:
```
input_data/
├── images/
├── sparse/
└── database.db
```

| Argument                    | Beschreibung                                                  |
|----------------------------|---------------------------------------------------------------|
| `--pipeline_type="colmap_to_transforms"`     | für Splatfacto vorbereiten                                   |
| `--pipeline_type="colmap_to_splat"`          | vollständige Pipeline inkl. .ply für Training                |

#### Für vorbereitete COLMAP-Daten für Splatfacto ` input_data` :

Ordnerstruktur:
```
input_data/
├── colmap/
│   ├── sparse/
│   └── database.db
├── images/
├── images_2/
├── images_4/
├── images_8/
├── sparse_pc/
└── transforms.json
```

| Argument                    | Beschreibung                                                  |
|----------------------------|---------------------------------------------------------------|
| `--pipeline_type="transforms_to_splat"`      | vollständige Pipeline inkl. .ply für Training                |

#### Zusätzliche Filterung:

| Option             | Wirkung                                                                   |
|--------------------|---------------------------------------------------------------------------|
| `--pre_filter_img`  |Filterung vor raft_extractor Bilderauswahl z.B. --pre_filter_img="30" Behalte 30% der schärften Bilder (zusätzlich feste 5 % extra Filterung von unbrauchbaren Bildern  |
| `--post_filter_img` |Filterung nach raft_extractor Bilderauswahl z.B. --pre_filter_img="60" Behalte 60% der schärften Bilder  |
|`--train_img_percentage`|Vie viele Bilder für das Splat Training genutzt werden z.B. --train_img_percentage="90" Trainiere den Splat mit 90% der verbleibenden Bilder |
#### Pipeline starten:

```bash
sbatch gpu_job.sbatch
```

---

### 🛠️ Fehlerbehebung

Fehlermeldung:
```
sbatch: error: Batch script contains DOS line breaks (\r\n)
sbatch: error: instead of expected UNIX line breaks (\n).
```

Beheben mit:
```bash
sed -i 's/\r$//' gpu_job.sbatch
sbatch gpu_job.sbatch
```
```
Sicherstellen das die Pointcloud in sparse/0 liegt
Sollte Sie z.B. in sparse/1 liegen, alle anderen Pointcloud Ordner löschen
und in Pipeline.py für den gewünschten Schritt bei prepare_colmap_data_for_splatfacto()
os.path.join(input_data_dir, "sparse/0")) ---> os.path.join(input_data_dir, "sparse/1"))
```
---

### 🧩 scripts-Verzeichnis

- Enthält `pipeline.py` → steuert den Ablauf im Container  
- Kann modifiziert werden, um die Pipeline anzupassen  
- Output liegt in `result_data/` als `splat.ply`, Trainingsdaten, und Rohdaten von Splatfacto

---

## 💻 Lokale Ausführung

### Vorbereitung:

1. **Windows:** Docker Desktop installieren  
   👉 [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)  
   - WSL2 aktivieren  
   - ggf. `.wslconfig` anpassen

2. **Linux:**  
   👉 [https://docs.docker.com/engine/install/ubuntu/](https://docs.docker.com/engine/install/ubuntu/)

3. **NVIDIA Container Toolkit installieren:**  
   👉 [https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

4. **Verzeichnisstruktur anlegen:**
```
MeinVerzeichnis/
├── input_data/
├── result_data/
└── scripts/
```

5. Docker-Image bauen:
```bash
cd <FULL_PATH_TO>/Docker
docker build -t <IMAGE_NAME> .
```

6. Container starten:
```bash
docker run -it --gpus all \
  -v <FULL_PATH_TO>/input_data:/mnt/input_data \
  -v <FULL_PATH_TO>/result_data:/mnt/result_data \
  -v <FULL_PATH_TO>/scripts:/mnt/pipeline_scripts \
  -p 7007:7007 <IMAGE_NAME> \
  python3 /mnt/pipeline_scripts/pipeline.py \
  --pipeline_type="mp4_to_splat" \
  --is_big_dataset="False" && echo "pipeline.py done"
```
oder mit Mockup.sh unter `pipeline_assets/jobscripts/Mockup.sh` 

7. Output liegt in `result_data/`

---

## 📦 DockerHub Image

🔗 [https://hub.docker.com/repository/docker/kiwil23/splat_tools_slim/general](https://hub.docker.com/repository/docker/kiwil23/splat_tools_slim/general)
