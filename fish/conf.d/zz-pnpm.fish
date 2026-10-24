# Load after vite-plus.fish so standalone pnpm takes precedence.
if test -d $HOME/.local/share/pnpm
  set -gx PNPM_HOME "$HOME/.local/share/pnpm"
  fish_add_path --path --move --prepend "$PNPM_HOME/bin"
end
