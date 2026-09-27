import pathlib, chardet

p = pathlib.Path("app.py")
b = p.read_bytes()
enc = chardet.detect(b)["encoding"] or "latin-1"
print("Detected encoding:", enc)

# backup first
pathlib.Path("app.py.bak").write_bytes(b)

# transcode to UTF-8
text = b.decode(enc, errors="replace")
p.write_text(text, encoding="utf-8")
print("Converted -> UTF-8 and created app.py.bak")
