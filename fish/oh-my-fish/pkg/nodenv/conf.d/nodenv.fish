if test -d $HOME/.nodenv
  set -Ux fish_user_paths $HOME/.nodenv/bin $fish_user_paths

  source (nodenv init - | psub)
end
