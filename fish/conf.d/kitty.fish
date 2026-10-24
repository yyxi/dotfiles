if set -q KITTY_INSTALLATION_DIR
  set --global KITTY_SHELL_INTEGRATION enabled no-cursor
  source "$KITTY_INSTALLATION_DIR/shell-integration/fish/vendor_conf.d/kitty-shell-integration.fish"
  set --prepend fish_complete_path "$KITTY_INSTALLATION_DIR/shell-integration/fish/vendor_completions.d"
end

if test -n "$SSH_CLIENT" && test -n "$SSH_TTY"
  true
else if type -q kitten && [ "$TERM" = "xterm-kitty" ]
  alias ssh="kitten ssh"
end
