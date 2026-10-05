#!/usr/bin/env python3
"""Install/remove an optional, backed-up Subspace loader in Hyprland bindings.lua."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import tempfile

BEGIN = "-- BEGIN pietrovos.subspace shortcuts\n"
END = "-- END pietrovos.subspace shortcuts\n"
BLOCK = BEGIN + '''do
  local path = os.getenv("HOME") .. "/.config/omarchy/plugins/pietrovos.subspace/bindings.lua"
  local file = io.open(path, "r")
  if file then
    file:close()
    dofile(path)
  end
end
''' + END


def updated_config(text, install):
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise ValueError("Subspace markers are incomplete or duplicated; resolve them manually.")
        start = text.index(BEGIN)
        end = text.index(END) + len(END)
        if end <= start:
            raise ValueError("Subspace markers are out of order.")
        # Leave user edits outside the owned block intact.
        return text[:start] + (BLOCK if install else "") + text[end:]
    if not install:
        return text
    # The separator belongs to the managed block so removal restores the original.
    if text and not text.endswith("\n"):
        raise ValueError("bindings.lua must end with a newline; add one before installing.")
    return text + BLOCK


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--install", action="store_true")
    actions.add_argument("--remove", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="print the proposed config without writing")
    args = parser.parse_args()
    path = Path.home() / ".config/hypr/bindings.lua"
    if path.is_symlink():
        parser.error("bindings.lua is a symlink; add/remove the README loader manually in its source.")
    if not path.is_file():
        parser.error("expected Omarchy Quattro ~/.config/hypr/bindings.lua")
    if args.install:
        plugin = Path.home() / ".config/omarchy/plugins/pietrovos.subspace"
        if not (plugin / "bindings.lua").is_file() or not (plugin / "scripts/subspace.py").is_file():
            parser.error("install the Subspace plugin first")
    text = path.read_text()
    try:
        updated = updated_config(text, args.install)
    except ValueError as error:
        parser.error(str(error))
    if args.dry_run:
        print(updated, end="")
        return
    if updated == text:
        print("Subspace shortcuts already " + ("installed." if args.install else "removed."))
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = path.with_name(path.name + ".subspace-backup." + stamp)
    shutil.copy2(path, backup)
    fd, temporary = tempfile.mkstemp(prefix=".subspace-bindings.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(updated)
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"Shortcuts {'installed' if args.install else 'removed'}. Backup: {backup}")
    print("Run: hyprctl reload && hyprctl configerrors")
    print("If you manage dotfiles with chezmoi, run: chezmoi add ~/.config/hypr/bindings.lua")


if __name__ == "__main__":
    main()
