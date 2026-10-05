import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


subspace = load("subspace", "subspace.py")
setup = load("setup", "setup-shortcuts.py")


def clients(groups, workspace=1):
    return [
        {"address": address, "stableId": address, "grouped": group,
         "workspace": {"id": workspace}}
        for group in groups for address in group
    ]


class GroupIdentityTests(unittest.TestCase):
    def named(self, members):
        state = subspace.reconcile({}, clients([members]), "session-a")
        group_id = next(iter(state["groups"]))
        state["groups"][group_id]["name"] = "Coding"
        return state, group_id

    def test_workspace_move_and_reorder_keep_identity(self):
        state, group_id = self.named(["a", "b", "c"])
        updated = subspace.reconcile(state, clients([["c", "a", "b"]], workspace=9), "session-a")
        self.assertEqual(updated, state)
        self.assertEqual(updated["groups"][group_id]["name"], "Coding")

    def test_addition_and_removal_keep_name(self):
        state, group_id = self.named(["a", "b", "c"])
        added = subspace.reconcile(state, clients([["a", "b", "c", "d"]]), "session-a")
        removed = subspace.reconcile(added, clients([["b", "c", "d"]]), "session-a")
        self.assertEqual(removed["groups"][group_id]["name"], "Coding")

    def test_split_keeps_name_on_largest_surviving_group(self):
        state, group_id = self.named(["a", "b", "c"])
        updated = subspace.reconcile(state, clients([["a"], ["b", "c"]]), "session-a")
        self.assertEqual(updated["groups"][group_id]["members"], ["b", "c"])
        self.assertEqual(sum(g["name"] == "Coding" for g in updated["groups"].values()), 1)

    def test_merge_retains_larger_group_name(self):
        state = subspace.reconcile({}, clients([["a"], ["b", "c"]]), "session-a")
        for group in state["groups"].values():
            group["name"] = "Large" if len(group["members"]) == 2 else "Small"
        updated = subspace.reconcile(state, clients([["a", "b", "c"]]), "session-a")
        self.assertEqual(next(iter(updated["groups"].values()))["name"], "Large")

    def test_new_session_cannot_inherit_reused_window_ids(self):
        state, _ = self.named(["a", "b"])
        updated = subspace.reconcile(state, clients([["a", "b"]]), "session-b")
        self.assertEqual(next(iter(updated["groups"].values()))["name"], "")

    def test_ungrouped_clients_do_not_create_subspaces(self):
        client = {"address": "a", "grouped": []}
        self.assertEqual(subspace.reconcile({}, [client], "session-a")["groups"], {})

    def test_snapshot_rename_and_cancel_preserve_state(self):
        live = clients([["a", "b"]])
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(subspace, "STATE", Path(directory)), patch.object(
                subspace, "hypr", side_effect=lambda query: live if query == "clients" else live[0].copy()
            ):
                active = subspace.snapshot()
                renamed = subspace.snapshot(active["subspaceId"], "Coding")
                self.assertEqual(renamed["subspaceName"], "Coding")
                with patch("sys.argv", ["subspace.py", "rename"]), patch.object(
                    subspace.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "")
                ):
                    subspace.main()
                self.assertEqual(subspace.snapshot()["subspaceName"], "Coding")
                self.assertEqual(subspace.snapshot(active["subspaceId"], "")["subspaceName"], "")
                self.assertEqual(json.loads((Path(directory) / "groups.json").read_text())["version"], 2)


class NavigationTests(unittest.TestCase):
    def test_absent_positions_and_no_group_do_not_dispatch(self):
        for active in [{"address": "a", "grouped": []}, {"address": "a", "grouped": ["a", "b"]}]:
            with patch.object(subspace, "hypr", return_value=active), patch.object(subspace, "dispatch") as dispatch:
                for target in [-1, 0, 3]:
                    subspace.select_or_reorder("select", target)
                    subspace.select_or_reorder("reorder", target)
                dispatch.assert_not_called()

    def test_zero_selects_tenth_member(self):
        with patch.object(subspace, "hypr", return_value={"address": "a", "grouped": list("abcdefghij")}), patch.object(subspace, "dispatch") as dispatch:
            subspace.select_or_reorder("select", 0)
            dispatch.assert_called_once_with("hl.dsp.group.active({ index = 10 })")

    def test_reordering_both_directions_and_same_position(self):
        with patch.object(subspace, "hypr", return_value={"address": "b", "grouped": list("abcd")}), patch.object(subspace, "dispatch") as dispatch:
            subspace.select_or_reorder("reorder", 4)
            self.assertEqual(dispatch.call_count, 2)
            dispatch.assert_called_with("hl.dsp.group.move_window({ forward = true })")
            dispatch.reset_mock()
            subspace.select_or_reorder("reorder", 1)
            dispatch.assert_called_once_with("hl.dsp.group.move_window({ forward = false })")
            dispatch.reset_mock()
            subspace.select_or_reorder("reorder", 2)
            dispatch.assert_not_called()


class ShortcutSetupTests(unittest.TestCase):
    def test_install_idempotent_and_remove_preserves_user_edits(self):
        original = '-- Custom config\no.bind("SUPER + X", "Example", "example")\n'
        installed = setup.updated_config(original, True)
        self.assertEqual(setup.updated_config(installed, True), installed)
        edited = installed + '-- User added this later\n'
        self.assertEqual(setup.updated_config(edited, False), original + '-- User added this later\n')
        self.assertEqual(setup.updated_config(original, False), original)

    def test_broken_or_duplicate_markers_are_rejected(self):
        for text in [setup.BEGIN, setup.END, setup.BLOCK * 2, setup.END + setup.BEGIN]:
            with self.assertRaises(ValueError):
                setup.updated_config(text, True)

    def test_cli_dry_run_backup_install_remove_in_isolated_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = home / ".config/hypr/bindings.lua"
            path.parent.mkdir(parents=True)
            original = "-- Existing user bindings\n"
            path.write_text(original)
            path.chmod(0o640)
            plugin = home / ".config/omarchy/plugins/pietrovos.subspace"
            (plugin / "scripts").mkdir(parents=True)
            (plugin / "bindings.lua").write_text("-- Test stub\n")
            (plugin / "scripts/subspace.py").write_text("# Test stub\n")
            env = dict(os.environ, HOME=str(home))
            command = ["python3", str(ROOT / "scripts/setup-shortcuts.py")]
            subprocess.run(command + ["--install", "--dry-run"], env=env, check=True, capture_output=True)
            self.assertEqual(path.read_text(), original)
            self.assertEqual(list(path.parent.glob("*.subspace-backup.*")), [])
            subprocess.run(command + ["--install"], env=env, check=True, capture_output=True)
            self.assertEqual(path.read_text(), original + setup.BLOCK)
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            backups = list(path.parent.glob("*.subspace-backup.*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)
            subprocess.run(command + ["--install"], env=env, check=True, capture_output=True)
            self.assertEqual(len(list(path.parent.glob("*.subspace-backup.*"))), 1)
            subprocess.run(command + ["--remove"], env=env, check=True, capture_output=True)
            self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
