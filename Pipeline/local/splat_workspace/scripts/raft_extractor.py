import argparse
import cv2
import numpy as np
import os
import torch
from torchvision.models.optical_flow import raft_large, Raft_Large_Weights
import torchvision.transforms.functional as TF
from tqdm import tqdm  # Fortschrittsbalken

# Prüfe Gerät (ROCm-kompatibel)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# RAFT laden
weights = Raft_Large_Weights.DEFAULT
raft_model = raft_large(weights=weights).to(device)
raft_model.eval()

# Funktion zum Prüfen auf Unschärfe
def is_blurry(image, threshold=100.0):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return variance < threshold, variance

# Funktion zum Prüfen auf Überbelichtung
def is_overexposed(image, threshold=240.0):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mean_brightness = np.mean(gray)
    return mean_brightness > threshold, mean_brightness

# Bild-Vorverarbeitung für RAFT
def preprocess_raft(frame1, frame2):
    frame1 = cv2.resize(frame1, (960, 520))
    frame2 = cv2.resize(frame2, (960, 520))
    frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
    frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
    tensor1 = TF.to_tensor(frame1).unsqueeze(0).to(device)
    tensor2 = TF.to_tensor(frame2).unsqueeze(0).to(device)
    return tensor1, tensor2

# Berechne Bewegungsintensität via RAFT
def calculate_optical_flow(prev_frame, next_frame):
    img1, img2 = preprocess_raft(prev_frame, next_frame)
    with torch.no_grad():
        list_of_flows = raft_model(img1, img2)
    flow = list_of_flows[-1]
    magnitude = torch.norm(flow, dim=1)
    return magnitude.mean().item()

# Verarbeitung von Video
def process_video(input_video_path, output_frames_dir, motion_threshold=2.0, sharpness_threshold=100.0, exposure_threshold=240.0, debug=False):
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print("❌ Fehler beim Öffnen des Videos!")
        return

    os.makedirs(output_frames_dir, exist_ok=True)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    progress_bar = tqdm(total=total_frames, desc="🔍 Verarbeite Frames", unit="Frame", disable=debug)

    frame_idx = 0
    kept_count = 0
    prev_frame = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        b_is_blurry, variance = is_blurry(frame, threshold=sharpness_threshold)
        if b_is_blurry:
            if debug:
                print(f"[{frame_idx}] ❌ Unscharf: {variance:.2f}")
            frame_idx += 1
            progress_bar.update(1)
            continue

        b_is_overexposed, mean_brightness = is_overexposed(frame, threshold=exposure_threshold)
        if b_is_overexposed:
            if debug:
                print(f"[{frame_idx}] ❌ Überbelichtet: {mean_brightness:.2f}")
            frame_idx += 1
            progress_bar.update(1)
            continue

        if prev_frame is not None:
            motion_intensity = calculate_optical_flow(prev_frame, frame)
            if motion_intensity > motion_threshold:
                frame_filename = f"frame_{frame_idx:04d}.jpg"
                cv2.imwrite(os.path.join(output_frames_dir, frame_filename), frame)
                kept_count += 1
                if debug:
                    print(f"[{frame_idx}] ✅ Gespeichert (Bewegung: {motion_intensity:.3f}, Sharpness: {variance:.3f}, Mean_Brightness: {mean_brightness:.3f})")
                prev_frame = frame
            else:
                if debug:
                    print(f"[{frame_idx}] 🔸 Zu wenig Bewegung ({motion_intensity:.3f})")
        else:
            frame_filename = f"frame_{frame_idx:04d}.jpg"
            cv2.imwrite(os.path.join(output_frames_dir, frame_filename), frame)
            kept_count += 1
            if debug:
                print(f"[{frame_idx}] ✅ Erstes Bild gespeichert")
            prev_frame = frame

        frame_idx += 1
        progress_bar.update(1)

    cap.release()
    progress_bar.close()
    print(f"\n🎉 {kept_count} von {frame_idx} Frames wurden gespeichert in '{output_frames_dir}'")

# Verarbeitung von Einzelbildern
def process_images(input_images_dir, output_frames_dir, motion_threshold=2.0, sharpness_threshold=100.0, exposure_threshold=240.0, debug=False):
    image_files = sorted([
        os.path.join(input_images_dir, f)
        for f in os.listdir(input_images_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
    ])

    if not image_files:
        print("❌ Keine Bilder im Eingabeverzeichnis gefunden!")
        return

    os.makedirs(output_frames_dir, exist_ok=True)
    progress_bar = tqdm(total=len(image_files), desc="🔍 Verarbeite Bilder", unit="Bild", disable=debug)

    kept_count = 0
    prev_frame = None

    for idx, image_path in enumerate(image_files):
        frame = cv2.imread(image_path)
        if frame is None:
            if debug:
                print(f"[{idx}] ⚠️ Bild konnte nicht geladen werden: {image_path}")
            progress_bar.update(1)
            continue

        b_is_blurry, variance = is_blurry(frame, threshold=sharpness_threshold)
        if b_is_blurry:
            if debug:
                print(f"[{idx}] ❌ Unscharf: {variance:.2f}")
            progress_bar.update(1)
            continue

        b_is_overexposed, mean_brightness = is_overexposed(frame, threshold=exposure_threshold)
        if b_is_overexposed:
            if debug:
                print(f"[{idx}] ❌ Überbelichtet: {mean_brightness:.2f}")
            progress_bar.update(1)
            continue

        if prev_frame is not None:
            motion_intensity = calculate_optical_flow(prev_frame, frame)
            if motion_intensity > motion_threshold:
                frame_filename = f"frame_{idx:04d}.jpg"
                cv2.imwrite(os.path.join(output_frames_dir, frame_filename), frame)
                kept_count += 1
                if debug:
                    print(f"[{idx}] ✅ Gespeichert (Bewegung: {motion_intensity:.3f}, Sharpness: {variance:.3f}, Mean_Brightness: {mean_brightness:.3f})")
                prev_frame = frame
            else:
                if debug:
                    print(f"[{idx}] 🔸 Zu wenig Bewegung ({motion_intensity:.3f})")
        else:
            frame_filename = f"frame_{idx:04d}.jpg"
            cv2.imwrite(os.path.join(output_frames_dir, frame_filename), frame)
            kept_count += 1
            if debug:
                print(f"[{idx}] ✅ Erstes Bild gespeichert")
            prev_frame = frame

        progress_bar.update(1)

    progress_bar.close()
    print(f"\n🎉 {kept_count} von {len(image_files)} Bildern wurden gespeichert in '{output_frames_dir}'")

# CLI-Parser
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrahiere sinnvolle Frames aus Video oder Einzelbildern basierend auf Schärfe, Helligkeit und Bewegung")
    parser.add_argument('--in', dest='input_path', required=True, help='Pfad zum Video oder Bildordner')
    parser.add_argument('--out', dest='output_dir', required=True, help='Verzeichnis zum Speichern der Frames')
    parser.add_argument('--motion_threshold', type=float, default=2.0, help='Bewegungsschwelle (mittlere Flow-Magnitude)')
    parser.add_argument('--sharpness_threshold', type=float, default=100.0, help='Unschärfeschwelle')
    parser.add_argument('--exposure_threshold', type=float, default=240.0, help='Helligkeitsschwelle')
    parser.add_argument('--debug', action='store_true', help='Aktiviere Debugmodus mit detaillierten Ausgaben')

    args = parser.parse_args()

    if os.path.isdir(args.input_path):
        process_images(
            args.input_path,
            args.output_dir,
            motion_threshold=args.motion_threshold,
            sharpness_threshold=args.sharpness_threshold,
            exposure_threshold=args.exposure_threshold,
            debug=args.debug
        )
    else:
        process_video(
            args.input_path,
            args.output_dir,
            motion_threshold=args.motion_threshold,
            sharpness_threshold=args.sharpness_threshold,
            exposure_threshold=args.exposure_threshold,
            debug=args.debug
        )
