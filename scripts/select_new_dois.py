#!/usr/bin/env python3
import pathlib
from typing import List, Set


def existing_dois(evidence_dir: pathlib.Path) -> Set[str]:
    import re, yaml
    out: Set[str] = set()
    for md in evidence_dir.rglob("*.md"):
        try:
            txt = md.read_text(encoding="utf-8", errors="ignore")
            m = re.match(r"^---\n(.*?)\n---\n", txt, flags=re.S)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            du = fm.get("doi_url")
            if isinstance(du, str) and du.strip():
                m2 = re.search(r"(10\.\d{4,9}/\S+)", du)
                if m2:
                    out.add(m2.group(1))
        except Exception:
            continue
    return out


def main(argv: List[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Filter cleaned DOIs to only new ones not present in evidence")
    ap.add_argument("input", help="Cleaned DOIs text file")
    ap.add_argument("--evidence", default="evidence", help="Evidence directory")
    ap.add_argument("-o", "--out", required=True, help="Output file for new DOIs to seed")
    args = ap.parse_args(argv)

    inp = pathlib.Path(args.input)
    evdir = pathlib.Path(args.evidence)
    outp = pathlib.Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    already = existing_dois(evdir) if evdir.exists() else set()
    lines = [l.strip() for l in inp.read_text(encoding="utf-8").splitlines() if l.strip()]
    new = [d for d in lines if d not in already]
    outp.write_text("\n".join(new) + ("\n" if new else ""), encoding="utf-8")
    print(f"existing={len(already)} cleaned_in={len(lines)} new_to_seed={len(new)} -> {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

