import pathlib
import re


def parse_name(line: str):
    # Strip comments and environment markers
    line = line.split('#', 1)[0]
    line = line.split(';', 1)[0]
    line = line.strip()
    if not line:
        return None
    # Remove version/constraint and extras
    name = re.split(r'[<>=!~]', line, 1)[0].strip()
    name = name.split('[', 1)[0].strip()
    return name.lower() or None


def ensure_requirements(path: pathlib.Path, needed: set[str]) -> list[str]:
    if path.exists():
        cur: set[str] = set()
        for l in path.read_text(encoding='utf-8').splitlines():
            n = parse_name(l)
            if n:
                cur.add(n)
        missing = sorted(n for n in needed if n not in cur)
        if missing:
            with path.open('a', encoding='utf-8', newline='\n') as f:
                for n in missing:
                    f.write(f"{n}\n")
        return missing
    else:
        content = "\n".join(sorted(needed)) + "\n"
        path.write_text(content, encoding='utf-8')
        return sorted(needed)


if __name__ == "__main__":
    req = pathlib.Path('requirements.txt')
    needed = {"requests", "pyyaml"}
    added = ensure_requirements(req, needed)
    if added:
        print(f"Appended: {', '.join(added)}")
    else:
        print("Already present; no changes.")
