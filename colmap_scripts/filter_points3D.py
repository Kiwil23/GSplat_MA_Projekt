import argparse
import os
import shutil
import numpy as np
import open3d as o3d
import read_write_model as rw

# --- Argumente parsen ---
parser = argparse.ArgumentParser(description="Filtere COLMAP Sparse-Modell (points3D.bin) in einem Ordner.")
parser.add_argument('--in', dest='input_dir', required=True, help='Pfad zum COLMAP Sparse-Ordner')
parser.add_argument('--out', dest='output_dir', required=True, help='Zielordner für das gefilterte Modell')
parser.add_argument('--min_views', type=int, default=3, help='Minimale Anzahl an Beobachtungen pro Punkt')
parser.add_argument('--max_error', type=float, default=1.0, help='Maximaler Reprojection Error pro Punkt')
parser.add_argument('--sor', action='store_true', help='Statistical Outlier Removal anwenden')
parser.add_argument('--cluster_filter', action='store_true', help='Nur größtes Cluster behalten')
parser.add_argument('--sor_k', type=int, default=20, help='SOR: Anzahl Nachbarn')
parser.add_argument('--sor_std', type=float, default=2.0, help='SOR: Standardabweichungsgrenze')
parser.add_argument('--cluster_eps', type=float, default=0.5, help='DBSCAN eps (Abstand in Metern)')
parser.add_argument('--cluster_min_points', type=int, default=10, help='DBSCAN: minimale Punkte im Cluster')
args = parser.parse_args()

# --- Ordner vorbereiten ---
if not os.path.isdir(args.input_dir):
    raise FileNotFoundError(f"Eingabeordner '{args.input_dir}' existiert nicht.")

if os.path.exists(args.output_dir):
    print(f"⚠️ Ausgabeordner '{args.output_dir}' existiert bereits. Inhalt wird überschrieben.")
    shutil.rmtree(args.output_dir)

print(f"📁 Kopiere Modell von '{args.input_dir}' nach '{args.output_dir}' ...")
shutil.copytree(args.input_dir, args.output_dir)

# --- Pfad zur points3D.bin im Zielordner ---
points3D_path = os.path.join(args.output_dir, "points3D.bin")

if not os.path.exists(points3D_path):
    raise FileNotFoundError(f"points3D.bin wurde im Zielordner nicht gefunden: {points3D_path}")

# --- Punkte laden ---
print(f"📥 Lade Punkte aus '{points3D_path}' ...")
points3D = rw.read_points3D_binary(points3D_path)
print(f"🔢 Gesamtpunkte: {len(points3D)}")

# --- Filtern nach min_views und reprojection error ---
filtered_points = {}
xyz_list = []
pid_list = []

for pid, pt in points3D.items():
    if len(pt.image_ids) >= args.min_views and pt.error < args.max_error:
        filtered_points[pid] = pt
        xyz_list.append(pt.xyz)
        pid_list.append(pid)

print(f"✅ Nach Basisfilter: {len(filtered_points)} Punkte")

# --- Optional: Open3D Outlier Removal ---
if args.sor or args.cluster_filter:
    print("🔍 Wandle Punktwolke für Open3D um ...")
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.array(xyz_list))

    if args.sor:
        print("📉 Wende Statistical Outlier Removal an ...")
        pcd, ind = pcd.remove_statistical_outlier(nb_neighbors=args.sor_k, std_ratio=args.sor_std)
        pid_list = [pid_list[i] for i in ind]

    if args.cluster_filter:
        print("🔗 Starte DBSCAN Cluster-Filterung ...")
        labels = np.array(pcd.cluster_dbscan(eps=args.cluster_eps,
                                             min_points=args.cluster_min_points,
                                             print_progress=True))
        if labels.max() < 0:
            print("⚠️ Keine Cluster gefunden. Breche Cluster-Filterung ab.")
        else:
            largest_cluster = np.argmax(np.bincount(labels[labels >= 0]))
            keep_indices = np.where(labels == largest_cluster)[0]
            pid_list = [pid_list[i] for i in keep_indices]

# --- Final: Neue Punkte sammeln ---
final_points = {pid: points3D[pid] for pid in pid_list}
print(f"✅ Finale Anzahl Punkte: {len(final_points)}")

# --- Speichern ---
rw.write_points3D_binary(final_points, points3D_path)
print(f"💾 Gefilterte Punkte gespeichert in: {points3D_path}")

