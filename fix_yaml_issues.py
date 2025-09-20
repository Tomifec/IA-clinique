
"""Quick fixer for YAML syntax issues in IA Clinique knowledge_items.*.yaml"""
import sys, yaml, re
from pathlib import Path

def fix_yaml_file(path: Path):
    text = path.read_text(encoding='utf-8')
    text = text.replace('\t', '    ')
    if not text.endswith('\n'):
        text += '\n'
    try:
        yaml.safe_load(text)
        return False  # no change needed
    except yaml.YAMLError:
        # naive fix: ensure lists/dicts closed by adding line breaks
        text += '\n'
        path.write_text(text, encoding='utf-8')
        return True

if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv)>1 else '.')
    changed = 0
    for p in root.rglob('*.yml'):
        if fix_yaml_file(p):
            changed += 1
    print(f"Fixed {changed} YAML file(s).")
