
import pathlib, re
p = pathlib.Path("requirements.txt")
need = {"requests","pyyaml","jsonschema","markdown-it-py"}
def parse_name(line: str):
    line = line.split("#",1)[0].split(";",1)[0].strip()
    if not line: return None
    return re.split(r"[<>=!~]", line, 1)[0].split("[",1)[0].strip().lower()
if p.exists():
    cur=set()
    for l in p.read_text(encoding="utf-8").splitlines():
        n=parse_name(l)
        if n: cur.add(n)
    miss=[n for n in need if n not in cur]
    if miss:
        with p.open("a", encoding="utf-8", newline="\n") as f:
            for n in miss: f.write(f"{n}\n")
        print("Appended:", ", ".join(miss))
    else:
        print("Already present; no changes.")
else:
    p.write_text("\n".join(sorted(need))+"\n", encoding="utf-8")
    print("Created requirements.txt")
