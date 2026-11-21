import os

RAW = "data/raw"
for folder in sorted(os.listdir(RAW)):
    path = os.path.join(RAW, folder)
    count, size = 0, 0
    for root, _, files in os.walk(path):
        for f in files:
            count += 1
            size += os.path.getsize(os.path.join(root, f))
    flag = "  <-- EMPTY" if count == 0 else ""
    print(f"{folder:35} {count:7} files  {size/1e6:10.1f} MB{flag}")