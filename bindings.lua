-- Optional Subspace bindings. Loaded AFTER the user's existing bindings.
local helper = os.getenv("HOME") .. "/.config/omarchy/plugins/pietrovos.subspace/scripts/subspace.py"
local quoted_helper = "'" .. helper:gsub("'", "'\\''") .. "'"

local function bind(keys, description, command)
  hl.unbind(keys)
  o.bind(keys, description, command)
end

bind("ALT + G", "Move active window out of subspace", hl.dsp.window.move({ out_of_group = true }))
bind("ALT + mouse_down", "Next window in subspace", hl.dsp.group.next())
bind("ALT + mouse_up", "Previous window in subspace", hl.dsp.group.prev())
for index = 1, 10 do
  local key = index == 10 and "0" or tostring(index)
  bind("ALT + " .. key, "Switch to subspace window " .. index, "python3 " .. quoted_helper .. " select " .. index)
  bind("ALT + SHIFT + " .. key, "Move subspace window to position " .. index, "python3 " .. quoted_helper .. " reorder " .. index)
end
bind("SUPER + ALT + N", "Name group subspace", "python3 " .. quoted_helper .. " rename")
