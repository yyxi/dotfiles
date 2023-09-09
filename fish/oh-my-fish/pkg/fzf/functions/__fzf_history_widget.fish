function __fzf_history_widget -d "Show command history"
  begin
    set -lx FZF_DEFAULT_OPTS "$FZF_DEFAULT_OPTS --tiebreak=index --bind=ctrl-r:toggle-sort,ctrl-z:ignore +m"
    history -z | eval fzf --read0 --print0 -q '(commandline)' | read -lz result
    and commandline -- $result
  end

  commandline -f repaint
end
