import pathlib, chardet, ast

p = pathlib.Path("app.py")
assert p.exists(), "app.py not found in current folder"

# detect current encoding (for logging only)
b = p.read_bytes()
det = chardet.detect(b); enc = det.get("encoding") or "latin-1"
print("Detected before:", enc)

# decode with a safe source encoding (prefer detected; fallback to iso-8859-9, then latin-1)
for src in [enc, "iso-8859-9", "latin-1"]:
    try:
        text = b.decode(src, errors="strict")
        print("Decoded successfully using:", src)
        break
    except Exception as e:
        last_err = e
else:
    raise RuntimeError(f"Could not decode app.py: {last_err}")

# write as UTF-8 with BOM (helps Windows tools recognize it)
backup = pathlib.Path("app.py.bak")
backup.write_bytes(b)
p.write_text(text, encoding="utf-8-sig")
print("Wrote app.py as UTF-8-SIG. Backup at app.py.bak")

# verify: strict UTF-8 decode
b2 = p.read_bytes()
try:
    _ = b2.decode("utf-8", errors="strict")
    print("UTF-8 verification: OK")
except Exception as e:
    raise RuntimeError(f"UTF-8 verification failed: {e}")

# verify: Python can compile it
try:
    ast.parse(_)
    print("Python AST parse: OK")
except SyntaxError as e:
    raise RuntimeError(f"Python parse failed: {e}")
