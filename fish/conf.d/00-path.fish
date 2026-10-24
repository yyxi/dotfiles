# Shared paths must be available before tool-specific command checks.
if test -d /usr/local/sbin
  fish_add_path /usr/local/sbin
end

if test -d /usr/local/bin
  fish_add_path /usr/local/bin
end

fish_add_path $HOME/bin
fish_add_path $HOME/.dotfiles/bin
fish_add_path $HOME/.local/bin
