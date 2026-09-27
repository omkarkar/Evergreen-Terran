import pathlib, chardet

for f in pathlib.Path(".").glob("*.py"):
    raw = open(f, "rb").read()
    enc = chardet.detect(raw)["encoding"]
    print(f"{f.name:35} -> {enc}")
