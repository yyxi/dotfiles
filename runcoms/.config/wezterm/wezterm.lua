local wezterm = require("wezterm")
local mux = wezterm.mux

local function assign(t1, t2)
  -- Iterate over the second table and add its key-value pairs to the first table
  for k, v in pairs(t2) do
    t1[k] = v
  end

  -- Return the modified first table
  return t1
end

local function expandPath(path)
  -- Check if the path starts with '~' and replace it with the home directory.
  if path:sub(1, 1) == "~" then
    -- Get the home directory and concatenate with the rest of the path
    local home = os.getenv("HOME")
    if home then
      return home .. path:sub(2)
    end
  end

  -- Return the original path if it doesn't start with '~' or if the home directory can't be determined
  return path
end

local cache_dir = expandPath("~/.cache/wezterm/")
local window_size_cache_path = cache_dir .. "window_size_cache.txt"
local font_size_cache_path = cache_dir .. "font_size_cache.txt"

local function font_size_read()
  local font_size_cache_file = io.open(font_size_cache_path, "r")

  if font_size_cache_file ~= nil then
    _, _, font_size = string.find(font_size_cache_file:read(), "(%d+%.?%d*)")

    font_size_cache_file:close()

    return tonumber(font_size)
  else
    return 17
  end
end

local function window_size_read()
  local window_size_cache_file = io.open(window_size_cache_path, "r")

  if window_size_cache_file ~= nil then
    _, _, initial_cols, initial_rows =
      string.find(window_size_cache_file:read(), "(%d+),(%d+)")

    window_size_cache_file:close()

    return {
      initial_cols = tonumber(initial_cols),
      initial_rows = tonumber(initial_rows),
    }
  else
    return { initial_cols = 80, initial_rows = 24 }
  end
end

local window_size = window_size_read()

c = wezterm.config_builder()

c.adjust_window_size_when_changing_font_size = false
c.audible_bell = "Disabled"
c.automatically_reload_config = false
c.check_for_updates = false
c.enable_scroll_bar = false
c.font_shaper = "Harfbuzz"
c.font_size = font_size_read()
c.initial_rows = window_size.initial_rows
c.initial_cols = window_size.initial_cols
c.force_reverse_video_cursor = true
c.freetype_load_flags = "NO_AUTOHINT"
c.freetype_load_target = "Light"
c.harfbuzz_features = { "kern", "liga", "clig", "calt", "dlig" }
c.hide_mouse_cursor_when_typing = false
c.hide_tab_bar_if_only_one_tab = true
c.native_macos_fullscreen_mode = false
c.scrollback_lines = 10000
c.show_tab_index_in_tab_bar = false
c.use_fancy_tab_bar = false
c.warn_about_missing_glyphs = false
c.window_close_confirmation = "NeverPrompt"
c.window_decorations = "RESIZE"

local fontFallbacks = {
  { family = "Apple Color Emoji", assume_emoji_presentation = true },
}

c.font = wezterm.font_with_fallback({
  {
    family = "Iosevka Custom",
    weight = "Medium",
    harfbuzz_features = c.harfbuzz_features,
  },
  table.unpack(fontFallbacks),
})

c.font_rules = {
  {
    italic = false,
    intensity = "Normal",
    font = c.font,
  },
  {
    italic = true,
    intensity = "Normal",
    font = wezterm.font_with_fallback({
      {
        family = "Iosevka Custom",
        weight = "Medium",
        style = "Italic",
        harfbuzz_features = c.harfbuzz_features,
      },
      table.unpack(fontFallbacks),
    }),
  },
  {
    italic = false,
    intensity = "Half",
    font = wezterm.font_with_fallback({
      {
        family = "Iosevka Custom",
        weight = "DemiBold",
        harfbuzz_features = c.harfbuzz_features,
      },
      table.unpack(fontFallbacks),
    }),
  },
  {
    italic = true,
    intensity = "Half",
    font = wezterm.font_with_fallback({
      {
        family = "Iosevka Custom",
        weight = "DemiBold",
        style = "Italic",
        harfbuzz_features = c.harfbuzz_features,
      },
      table.unpack(fontFallbacks),
    }),
  },
  {
    italic = false,
    intensity = "Bold",
    font = wezterm.font_with_fallback({
      {
        family = "Iosevka Custom",
        weight = "Bold",
        harfbuzz_features = c.harfbuzz_features,
      },
      table.unpack(fontFallbacks),
    }),
  },
  {
    italic = true,
    intensity = "Bold",
    font = wezterm.font_with_fallback({
      {
        family = "Iosevka Custom",
        weight = "Bold",
        style = "Italic",
        harfbuzz_features = c.harfbuzz_features,
      },
      table.unpack(fontFallbacks),
    }),
  },
}

c.window_padding = {
  left = "1cell",
  right = "1cell",
  top = "0.25cell",
  bottom = "0.5cell",
}

c.window_frame = {
  font = wezterm.font_with_fallback({
    {
      family = "Iosevka Custom",
      weight = "Bold",
      harfbuzz_features = c.harfbuzz_features,
    },
    { family = "Roboto", weight = "Bold" },
  }),
  -- The size of the font in the tab bar.
  -- Default to 10.0 on Windows but 12.0 on other systems
  font_size = 14.0,

  active_titlebar_bg = "#1d2021",
  inactive_titlebar_bg = "#1d2021",

  -- button_bg = '#1d2021',
  -- button_hover_bg = '#1d2021',
  --  inactive_titlebar_border_bottom = '#1d2021',
  --  active_titlebar_border_bottom = '#1d2021',
  --  inactive_titlebar_fg = '#cccccc',
  --  active_titlebar_fg = '#ffffff',
  --  button_fg = '#cccccc',
  --  button_hover_fg = '#ffffff',

  border_left_width = "0cell",
  border_right_width = "0cell",
  border_bottom_height = "0cell",
  border_top_height = "0.5cell",

  border_left_color = "#1d2021",
  border_right_color = "#1d2021",
  border_bottom_color = "#1d2021",
  border_top_color = "#1d2021",
}

colors, _ = wezterm.color.load_scheme(
  expandPath("~/.config/wezterm/gruvbox-dark-hard.toml")
)
c.colors = assign(colors, {
  tab_bar = {
    background = "#1d2021",
    inactive_tab_edge = "#1d2021",
    active_tab = {
      bg_color = "#1d2021",
      fg_color = "#ebdbb2",
      intensity = "Bold",
    },
    inactive_tab = {
      bg_color = "#1d2021",
      fg_color = "#ebdbb2",
      intensity = "Normal",
    },
    inactive_tab_hover = {
      bg_color = "#1d2021",
      fg_color = "#ebdbb2",
      intensity = "Normal",
    },
    new_tab = {
      bg_color = "#1d2021",
      fg_color = "#1d2021",
    },
    new_tab_hover = {
      bg_color = "#1d2021",
      fg_color = "#1d2021",
    },
  },
})

c.tab_max_width = 16

wezterm.on(
  "format-tab-title",
  function(tab, tabs, panes, config, hover, max_width)
    local background = "#1d2021"
    local foreground = "#ebdbb2"

    if tab.is_active then
      foreground = "#fabd2f"
    end

    local title = " " .. tab.active_pane.title .. " "
    local edge_foreground = background

    return {
      { Background = { Color = background } },
      { Foreground = { Color = background } },
      { Text = " " },
      { Background = { Color = background } },
      { Foreground = { Color = foreground } },
      { Text = title },
      { Background = { Color = background } },
      { Foreground = { Color = background } },
      { Text = " " },
    }
  end
)

wezterm.on("window-resized", function(window, pane)
  os.execute("mkdir -p " .. cache_dir)

  local window_size_cache_file = io.open(window_size_cache_path, "r")
  --
  -- if not window_size_cache_file == nil then
  local tab_size = pane:tab():get_size()

  cols = tab_size["cols"]
  rows = tab_size["rows"]

  contents = string.format("%d,%d", cols, rows)

  window_size_cache_file = assert(io.open(window_size_cache_path, "w"))
  window_size_cache_file:write(contents)
  window_size_cache_file:close()
  -- end
end)

local current_font_size = c.font_size

wezterm.on("decrease-font-size", function(window, pane)
  window:perform_action(wezterm.action.DecreaseFontSize, pane)
  current_font_size = current_font_size * 0.9

  local font_size_cache_file = io.open(font_size_cache_path, "r")
  font_size_cache_file = assert(io.open(font_size_cache_path, "w"))
  font_size_cache_file:write(string.format("%f", current_font_size))
  font_size_cache_file:close()
end)

wezterm.on("increase-font-size", function(window, pane)
  window:perform_action(wezterm.action.IncreaseFontSize, pane)
  current_font_size = current_font_size * 1.1

  local font_size_cache_file = io.open(font_size_cache_path, "r")
  font_size_cache_file = assert(io.open(font_size_cache_path, "w"))
  font_size_cache_file:write(string.format("%f", current_font_size))
  font_size_cache_file:close()
end)

wezterm.on("gui-startup", function(window)
  local window_size = window_size_read()

  local tab, pane, window = mux.spawn_window({
    width = window_size.initial_cols,
    height = window_size.initial_rows,
  })

  window = window:gui_window()
  local overrides = window:get_config_overrides() or {}

  overrides.font_size = font_size_read()
  current_font_size = overrides.font_size
  window:set_config_overrides(overrides)
  window:maximize()
end)

c.keys = {
  {
    key = "-",
    mods = "CTRL",
    action = wezterm.action.EmitEvent("decrease-font-size"),
  },
  {
    key = "=",
    mods = "CTRL",
    action = wezterm.action.EmitEvent("increase-font-size"),
  },
  {
    key = "_",
    mods = "CTRL",
    action = wezterm.action.EmitEvent("decrease-font-size"),
  },
  {
    key = "+",
    mods = "CTRL",
    action = wezterm.action.EmitEvent("increase-font-size"),
  },
  {
    key = "_",
    mods = "SHIFT|CTRL",
    action = wezterm.action.EmitEvent("decrease-font-size"),
  },
  {
    key = "+",
    mods = "SHIFT|CTRL",
    action = wezterm.action.EmitEvent("increase-font-size"),
  },
}

return c
