# GSplat_MA_Projekt

Pipeline mit Enroot Container ausführen

## Schritte:

1. Mit SSH verbinden:
   ```bash
   ssh login.ai.lrz.de -l xxyyyzz
   ```

2. Den Ordner `Containers` auf das `/home` Verzeichnis mit SSH SCP Command oder über das Frontend hochladen.

3. Eine interaktive Session starten:
   ```bash
   salloc -p lrz-hgx-h100-94x4 --gres=gpu:1
   ```
   Allocation mit `srun nvidia-smi` überprüfen. Wenn die H100 angezeigt wird, ist alles ok.

4. Docker Image mit Enroot importieren (funktioniert nur auf Computing-Knoten):
   ```bash
   srun enroot import docker://kiwil23/splat_tools_slim
   ```

5. Interaktive Session mit `exit` beenden, um Ressourcen wieder freizugeben.

6. Oder

7. `kiwil23_splat_tools_slim.sqsh` aus dem Repo herunterladen und mit SSH SCP Command oder über das Frontend hochladen.

8. `gpu_job.sbatch` Pfade anpassen.

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
