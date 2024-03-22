if type -q zoxide
  zoxide init --no-cmd --hook pwd fish  | source

  alias z=__zoxide_zi
end
