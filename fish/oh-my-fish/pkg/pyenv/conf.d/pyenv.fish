if test -d $HOME/.pyenv
  set -Ux PYENV_ROOT $HOME/.pyenv
  set -Ux PYENV_SHELL fish
  fish_add_path $PYENV_ROOT/bin $PYENV_ROOT/shims

  pyenv init - | source
end
