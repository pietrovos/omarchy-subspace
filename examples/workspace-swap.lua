-- Optional whole-workspace swapping, as demonstrated in the Subspace video.
-- Load after your existing bindings. Requires Omarchy Quattro's Hyprland Lua API.
local function swap_workspace(target)
  local current = hl.get_active_workspace()
  if not current or current.id <= 0 or current.id == target or hl.get_active_special_workspace() then
    return
  end

  local source = current.id
  local occupied = {}
  for _, workspace in ipairs(hl.get_workspaces()) do
    occupied[workspace.id] = true
  end

  if occupied[target] then
    local temporary = 11
    while occupied[temporary] do
      temporary = temporary + 1
    end
    hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(target), id = temporary }))
    hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(source), id = target }))
    hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(temporary), id = source }))
  else
    hl.dispatch(hl.dsp.workspace.change_id({ workspace = tostring(source), id = target }))
  end
end

for index = 1, 10 do
  local target = index
  local key = index == 10 and "0" or tostring(index)
  local keys = "SUPER + CTRL + SHIFT + " .. key
  hl.unbind(keys)
  o.bind(keys, "Swap workspace with " .. index, function()
    swap_workspace(target)
  end)
end
