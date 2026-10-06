# Whole-workspace swapping: the shortcut from the video

In the [Subspace walkthrough](https://github.com/pietrovos/omarchy-subspace/releases/download/v1.0.1/subspace-demo.mp4),
I use **Ctrl+Shift+Super+number** to rearrange workspaces without moving every
window or subspace individually. Super is the Windows/Command modifier used by
Omarchy; the order you hold the three modifiers does not matter.

This is a separate Hyprland customization. Subspace and its regular optional
shortcut installer do not enable it automatically. The bundled
[`examples/workspace-swap.lua`](../examples/workspace-swap.lua) contains the same
swap logic used in my personal config.

## What the shortcut does

| Shortcut | Destination |
| --- | --- |
| Ctrl+Shift+Super+1 through Ctrl+Shift+Super+9 | Workspaces 1–9 |
| Ctrl+Shift+Super+0 | Workspace 10 |

- It moves the **whole current workspace layout**, including all its windows,
  window groups/subspaces, and tile sizes, to the destination number.
- If the destination workspace exists, the two workspaces exchange numbers.
- If the destination is unused, the current workspace receives that number.
- Focus follows your original workspace/windows to their new number.
- Targeting the current number does nothing.
- It does nothing on special workspaces or while a special workspace is open.

For example, suppose your coding layout is on workspace 2 and your browsing
layout is on workspace 5. While focused on workspace 2, press
**Ctrl+Shift+Super+5**. Coding is now on 5, browsing is now on 2, and you stay with
your coding windows. Every group keeps its members and layout, and Subspace names
continue to follow their groups within the current Hyprland session.

This swaps entire workspaces, not just the focused subspace. If there are multiple
groups or ungrouped windows on that workspace, they all move together.
`Alt+Shift+number` is different: it reorders the focused tab within its group.

## Set up the shortcut

Requires **Omarchy Quattro's Lua-configured Hyprland**, including
`hl.dsp.workspace.change_id`. This is not a `hyprland.conf` binding snippet for
older Hyprland releases.

1. Install or update Subspace so the example is available:

   ```sh
   omarchy plugin update pietrovos.subspace
   ```

   For a fresh installation:

   ```sh
   omarchy plugin add https://github.com/pietrovos/omarchy-subspace.git --enable
   ```

2. Back up `~/.config/hypr/bindings.lua` before editing it. For example:

   ```sh
   cp ~/.config/hypr/bindings.lua ~/.config/hypr/bindings.lua.before-subspace-swap-$(date +%Y%m%d-%H%M%S)
   ```

3. Append the following block **once**, after your existing bindings in
   `~/.config/hypr/bindings.lua`. If that file is symlinked, edit its source instead.

   ```lua
   -- BEGIN pietrovos.subspace workspace swap
   do
     local path = os.getenv("HOME") .. "/.config/omarchy/plugins/pietrovos.subspace/examples/workspace-swap.lua"
     local file = io.open(path, "r")
     if file then
       file:close()
       dofile(path)
     end
   end
   -- END pietrovos.subspace workspace swap
   ```

   The example replaces any existing Hyprland bindings on
   `Super+Ctrl+Shift+1` through `Super+Ctrl+Shift+0`. Existing lines stay in your
   config, but these keys will run the swap action after this loader is enabled.
   It does not change your other shortcuts or groupbar appearance.

4. Apply and check the config:

   ```sh
   hyprctl reload
   hyprctl configerrors
   ```

   Resolve any reported errors before using the shortcut. If you manage your
   dotfiles with chezmoi, also track the loader:

   ```sh
   chezmoi add ~/.config/hypr/bindings.lua
   ```

You can instead copy the complete example into your own bindings file if you
want it independent of the plugin. To change the keys, edit your own copy rather
than the installed example, because plugin updates replace files in its folder.

## How it preserves the layout

The helper uses Hyprland's native `workspace.change_id` dispatcher instead of
moving windows one at a time. For an occupied destination, it uses an unused
temporary workspace ID starting at 11, then exchanges the two IDs. That preserves
the layout trees and group membership. An unused destination needs just one ID
change. The temporary ID is internal; you do not need to configure workspace 11.

Workspace-specific rules apply to workspace numbers, so review such rules if you
have custom per-workspace settings or monitor assignments.

### Workspace-bar display

Some Quickshell versions cache workspace IDs and window associations after a
`change_id` event. On those versions, a workspace widget using that cache can show
stale occupancy or highlighting after a swap. This does not mean the compositor
failed to swap the layouts. Check the actual state with:

```sh
hyprctl -j activeworkspace
hyprctl -j workspaces
```

My demo uses a separate customized workspace widget that reads this state directly
from `hyprctl`. That workspace widget is not included in Subspace. Restarting the
shell can refresh a stale display (`omarchy restart shell`), but a cache-based
widget can become stale again on a later swap. Subspace itself refreshes on
`changeworkspaceid` and reads its focused group through `hyprctl`.

## Remove the workspace-swap shortcuts

Delete the block between `BEGIN pietrovos.subspace workspace swap` and
`END pietrovos.subspace workspace swap`, including both marker lines, from your
bindings file. If you copied the example directly instead, remove that copied
section. Then run:

```sh
hyprctl reload
hyprctl configerrors
```

Any previous bindings on those keys become effective again after reloading.
Track the edit again if you use chezmoi. Remove the loader before uninstalling
Subspace; its missing-file guard also safely skips an already-removed plugin.
