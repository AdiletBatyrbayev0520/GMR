import argparse
import pathlib
import re
import sys


def rename_in_file(path: pathlib.Path, dry_run: bool = False) -> int:
    text = path.read_text()
    new_text = re.sub(r"\bLeftToeBase\b", "LeftToe", text)
    new_text = re.sub(r"\bRightToeBase\b", "RightToe", new_text)

    if new_text == text:
        return 0

    n = text.count("LeftToeBase") + text.count("RightToeBase")
    if dry_run:
        print(f"[dry-run] {path}: would replace {n} occurrence(s)")
    else:
        path.write_text(new_text)
        print(f"{path}: replaced {n} occurrence(s)")
    return n


def main():
    p = argparse.ArgumentParser(
        description="Rename LeftToeBase→LeftToe and RightToeBase→RightToe in files."
    )
    p.add_argument("paths", nargs="+", help="Files or directories to process.")
    p.add_argument(
        "--ext",
        default=".bvh",
        help="Extension to match when a path is a directory (default: .bvh). "
             "Use '*' to match all files.",
    )
    p.add_argument("--dry-run", action="store_true", help="Show changes without writing.")
    args = p.parse_args()

    targets: list[pathlib.Path] = []
    for raw in args.paths:
        path = pathlib.Path(raw)
        if not path.exists():
            print(f"warning: {path} does not exist", file=sys.stderr)
            continue
        if path.is_file():
            targets.append(path)
        else:
            pattern = "*" if args.ext == "*" else f"*{args.ext}"
            targets.extend(sorted(path.rglob(pattern)))

    if not targets:
        print("No files matched.", file=sys.stderr)
        sys.exit(1)

    total = 0
    for t in targets:
        try:
            total += rename_in_file(t, dry_run=args.dry_run)
        except UnicodeDecodeError:
            print(f"skipped (binary): {t}", file=sys.stderr)

    print(f"\nTotal replacements: {total}")


if __name__ == "__main__":
    main()



#   Usage:
#   # single file
#   python scripts/rename_toebase.py input_files/dastan2_mixamo.bvh

#   # whole directory (recursive, .bvh by default)
#   python scripts/rename_toebase.py input_files/
  
#   # preview without writing
#   python scripts/rename_toebase.py input_files/ --dry-run
  
#   # different extension or all files
#   python scripts/rename_toebase.py some_dir/ --ext .txt
#   python scripts/rename_toebase.py some_dir/ --ext '*'

#   Uses \b word boundaries so it won't accidentally match longer names that happen to contain LeftToeBase.
