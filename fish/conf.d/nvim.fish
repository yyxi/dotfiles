if test -d $HOME/.neovim-dist/bin
  fish_add_path $HOME/.neovim-dist/bin

  if test -d $HOME/.local/share/nvim/mason/bin
    fish_add_path $HOME/.local/share/nvim/mason/bin
  end
end

if type -q nvim
  alias vi=nvim
  alias vim=nvim

  set -x EDITOR nvim
  set -x VISUAL nvim
end
