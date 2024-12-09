if test -d $HOME/.goenv
  fish_add_path $HOME/.goenv/bin

  source (goenv init - | psub)
end
