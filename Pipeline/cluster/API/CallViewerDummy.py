import os
def main():
    print("CallViewerDummy cluster läuft")
    downloads_path = os.path.join(os.path.dirname(__file__), "downloads")

    # Liste alle Dateien im Ordner
    files = [f for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))]

    if len(files) == 1:
        dateiname = files[0]
        print(f"Datei im downloads-Ordner: {dateiname}")
    else:
        print(f"Es sind {len(files)} Dateien im downloads-Ordner. Erwartet wird genau 1 Datei.")


if __name__ == "__main__":
    main()