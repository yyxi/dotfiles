if test -d $HOME/.pyenv
  set -Ux PYENV_ROOT $HOME/.pyenv
  set -Ux fish_user_paths $PYENV_ROOT/bin $fish_user_paths

  source (pyenv init - | psub)
end
