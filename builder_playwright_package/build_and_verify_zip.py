"""Build the builder-crawler deploy zip from the live-extracted tree with the
patched lambda_function.py swapped in, then verify integrity.

We rebuild from the LIVE artifact tree (downloaded from the deployed function)
so the Playwright dependency layout is byte-identical to what prod already runs;
only lambda_function.py changes.
"""
import os
import shutil
import zipfile

LIVE_DIR = os.path.join(os.environ["TEMP"], "live-crawler")
PATCHED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lambda_function.py")
OUT = os.path.join(os.environ["TEMP"], "builder-crawler-fixed.zip")

# Swap the patched handler into the live tree.
shutil.copy2(PATCHED, os.path.join(LIVE_DIR, "lambda_function.py"))

if os.path.exists(OUT):
    os.remove(OUT)

count = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _dirs, files in os.walk(LIVE_DIR):
        for name in files:
            full = os.path.join(root, name)
            arc = os.path.relpath(full, LIVE_DIR).replace(os.sep, "/")
            zf.write(full, arc)
            count += 1

# Integrity check.
with zipfile.ZipFile(OUT) as zf:
    bad = zf.testzip()
    assert bad is None, f"corrupt entry: {bad}"
    names = zf.namelist()
    assert "lambda_function.py" in names, "lambda_function.py not at zip root"

size = os.path.getsize(OUT)
print(f"Built {OUT}")
print(f"  files: {count}, size: {size:,} bytes")
print(f"  lambda_function.py at root: yes, testzip: OK")
