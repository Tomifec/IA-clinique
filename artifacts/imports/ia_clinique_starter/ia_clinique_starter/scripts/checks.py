
import sys, os, re, json, yaml
from jsonschema import Draft7Validator

ROOT = os.path.dirname(os.path.dirname(__file__)) if __file__ else os.getcwd()
SCHEMAS = {
    "evidence": json.load(open(os.path.join(ROOT, "schemas", "evidence.schema.json"), encoding="utf-8")),
    "strategies": json.load(open(os.path.join(ROOT, "schemas", "strategies.schema.json"), encoding="utf-8")),
    "safety": json.load(open(os.path.join(ROOT, "schemas", "safety.schema.json"), encoding="utf-8")),
}

FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

def parse_front_matter(path):
    with open(path, encoding="utf-8") as f:
        txt = f.read()
    m = FM_RX.match(txt)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}

def validate_dir(kind, schema, dirpath):
    val = Draft7Validator(schema)
    errors = []
    if not os.path.isdir(dirpath):
        return errors
    for root, _, files in os.walk(dirpath):
        for fn in files:
            if not fn.lower().endswith(".md"): continue
            fm = parse_front_matter(os.path.join(root, fn))
            if fm is None:
                errors.append((os.path.join(root, fn), "missing_front_matter"))
                continue
            errs = sorted(val.iter_errors(fm), key=lambda e: e.path)
            for e in errs:
                errors.append((os.path.join(root, fn), e.message))
    return errors

def main():
    all_errors = []
    all_errors += validate_dir("evidence", SCHEMAS["evidence"], os.path.join(ROOT, "evidence"))
    all_errors += validate_dir("strategies", SCHEMAS["strategies"], os.path.join(ROOT, "strategies"))
    all_errors += validate_dir("safety", SCHEMAS["safety"], os.path.join(ROOT, "safety"))
    if all_errors:
        print("Schema validation failed:")
        for path, msg in all_errors:
            print(f" - {path}: {msg}")
        sys.exit(1)
    print("OK: all schemas valid.")
    sys.exit(0)

if __name__ == "__main__":
    main()
