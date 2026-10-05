#!/usr/bin/env python3
"""Name Hyprland groups by session-scoped stable window membership."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid


STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy/subspace"
SESSION = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")


def hypr(query):
    return json.loads(subprocess.check_output(["hyprctl", "-j", query], text=True))


def reconcile(state, clients, session):
    """Names follow surviving membership, with one identity per live group."""
    by_address = {client["address"]: client for client in clients}
    live = set()
    for client in clients:
        addresses = client.get("grouped", [])
        members = tuple(sorted(
            str(by_address[address].get("stableId") or address)
            for address in addresses if address in by_address
        ))
        if members:
            live.add(members)

    previous = state.get("groups", {}) if state.get("session") == session else {}
    candidates = []
    for group_id, group in previous.items():
        old = set(group["members"])
        for members in live:
            overlap = len(old.intersection(members))
            if overlap:
                candidates.append((overlap, overlap / len(old), group_id, members))
    assigned = {}
    used = set()
    for _, _, group_id, members in sorted(candidates, reverse=True):
        if group_id not in used and members not in assigned:
            assigned[members] = group_id
            used.add(group_id)

    groups = {}
    for members in sorted(live):
        group_id = assigned.get(members, uuid.uuid4().hex)
        name = previous.get(group_id, {}).get("name", "")
        groups[group_id] = {"members": list(members), "name": name}
    return {"version": 2, "session": session, "groups": groups}


def save(path, state):
    fd, temporary = tempfile.mkstemp(prefix="groups.", dir=STATE)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(state, output, indent=2)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def snapshot(rename_id=None, name=None):
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / "groups.json"
    with (STATE / "groups.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = json.loads(path.read_text())
        except FileNotFoundError:
            state = {}
        clients = hypr("clients")
        active = hypr("activewindow")
        updated = reconcile(state, clients, SESSION)
        if rename_id in updated["groups"]:
            updated["groups"][rename_id]["name"] = name
        if updated != state:
            save(path, updated)
        active_client = next((c for c in clients if c["address"] == active.get("address")), {})
        active_id = str(active_client.get("stableId") or active.get("address", ""))
        active["subspaceId"] = ""
        active["subspaceName"] = ""
        if active_client.get("grouped"):
            for group_id, group in updated["groups"].items():
                if active_id in group["members"]:
                    active["subspaceId"] = group_id
                    active["subspaceName"] = group["name"]
                    break
        return active


def dispatch(expression):
    subprocess.run(["hyprctl", "dispatch", expression], check=True, stdout=subprocess.DEVNULL)


def select_or_reorder(action, target):
    target = 10 if target == 0 else target
    active = hypr("activewindow")
    members = active.get("grouped", [])
    if target < 1 or target > len(members) or active.get("address") not in members:
        return
    if action == "select":
        dispatch(f"hl.dsp.group.active({{ index = {target} }})")
        return
    current = members.index(active["address"]) + 1
    forward = "true" if current < target else "false"
    for _ in range(abs(current - target)):
        dispatch(f"hl.dsp.group.move_window({{ forward = {forward} }})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=["snapshot", "rename", "select", "reorder"], default="snapshot")
    parser.add_argument("target", nargs="?", type=int)
    args = parser.parse_args()
    if args.action in ("select", "reorder"):
        if args.target is None:
            parser.error("select/reorder requires a numeric position")
        select_or_reorder(args.action, args.target)
        return
    active = snapshot()
    if args.action == "rename":
        group_id = active["subspaceId"]
        if not group_id:
            return
        current = active["subspaceName"]
        prompt = "Rename group subspace" + (f" ({current})" if current else "")
        result = subprocess.run(["omarchy-menu-input", prompt], capture_output=True, text=True)
        if result.returncode == 0:
            snapshot(group_id, result.stdout.rstrip("\n"))
    else:
        print(json.dumps(active))


if __name__ == "__main__":
    main()
