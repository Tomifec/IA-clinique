import argparse
import pathlib
import re


DOI_RX = re.compile(r"10\.\d{4,9}/\S+", re.I)
DOI_URL_RX = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/\S+)", re.I)


def extract(text: str):
    out = set()
    for m in DOI_URL_RX.finditer(text):
        out.add(m.group(1).rstrip(').,;'))
    for m in DOI_RX.finditer(text):
        out.add(m.group(0).rstrip(').,;'))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="Markdown files to scan")
    args = ap.parse_args()
    dois = set()
    for p in args.paths:
        path = pathlib.Path(p)
        if path.exists():
            txt = path.read_text(encoding="utf-8", errors="ignore")
            dois.update(extract(txt))
    for d in sorted(dois):
        print(d)


if __name__ == "__main__":
    main()

