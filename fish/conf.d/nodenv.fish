if test -d $HOME/.nodenv
  fish_add_path $HOME/.nodenv/bin

  source (nodenv init - | psub)
end
