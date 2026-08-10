# -*- coding: utf-8 -*-
"""Turn a .excalidraw FILE into the CLIPBOARD json Excalidraw accepts on Ctrl+V.

    python docs/diagrams/to_clipboard.py Homies-Current-System-Flow.excalidraw

The two formats are not the same, which is the whole reason this exists:

  * `{"type": "excalidraw", ...}`            - a file. Drag it in, or File > Open.
  * `{"type": "excalidraw/clipboard", ...}`  - a paste. Select all, copy, Ctrl+V
                                               onto any canvas, keeps whatever
                                               is already there.

Written compact (no indent) because the point is to select the whole thing in
one go and paste it; pretty-printing triples the line count for no gain.
"""
import io, json, os, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))

arg = sys.argv[1] if len(sys.argv) > 1 else "Homies-Current-System-Flow.excalidraw"
src = arg if os.path.isabs(arg) else os.path.join(HERE, arg)
if not os.path.exists(src):
    sys.exit("No such file: %s" % src)

doc = json.load(io.open(src, encoding="utf-8"))
els = [e for e in doc.get("elements", []) if not e.get("isDeleted")]
if not els:
    sys.exit("%s has no elements." % src)

clip = {"type": "excalidraw/clipboard", "elements": els,
        "files": doc.get("files", {})}

out = os.path.splitext(src)[0] + ".paste.json"
with io.open(out, "w", encoding="utf-8") as f:
    json.dump(clip, f, ensure_ascii=False, separators=(",", ":"))

print("wrote %s" % out)
print("elements: %d   chars: %d" % (len(els), os.path.getsize(out)))
print("\nSelect all in that file, copy, then Ctrl+V on excalidraw.com.")
