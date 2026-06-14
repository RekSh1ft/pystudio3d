"""
Run this once to download fonts into assets/fonts/
  python assets/fonts/get_fonts.py
"""
import urllib.request, os, zipfile, io

OUT = os.path.dirname(os.path.abspath(__file__))

DOWNLOADS = [
    # (url, zip_path_inside, output_filename)
    (
        "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip",
        "Inter Desktop/Inter-Regular.otf",
        "Inter-Regular.otf",
    ),
    (
        "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip",
        "fonts/ttf/JetBrainsMono-Regular.ttf",
        "JetBrainsMono-Regular.ttf",
    ),
]

for url, inner, out_name in DOWNLOADS:
    dest = os.path.join(OUT, out_name)
    if os.path.exists(dest):
        print(f"already exists: {out_name}")
        continue
    print(f"downloading {out_name}...")
    data = urllib.request.urlopen(url).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    with open(dest, "wb") as f:
        f.write(z.read(inner))
    print(f"  saved {out_name}")

print("done")
