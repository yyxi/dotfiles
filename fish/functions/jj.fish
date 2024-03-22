function jj -d "List files"
  set -l commandline (__fzf_parse_commandline)
  set -l dir $commandline[1]
  set -l fzf_query $commandline[2]
  set -l prefix $commandline[3]

  # "-path \$dir'*/\\.*'" matches hidden files/folders inside $dir but not
  # $dir itself, even if hidden.
  # test -n "$FZF_CTRL_T_COMMAND"; or set -l FZF_CTRL_T_COMMAND "
  # command find -L \$dir -mindepth 1 \\( -path \$dir'*/\\.*' -o -fstype 'sysfs' -o -fstype 'devfs' -o -fstype 'devtmpfs' \\) -prune \
  # -o -type f -print \
  # -o -type d -print \
  # -o -type l -print 2> /dev/null | sed 's@^\./@@'"

  set -l FZF_CTRL_T_COMMAND "command fd -L -H --min-depth 1 --type f \$dir 2> /dev/null"

  begin
    set -lx FZF_DEFAULT_OPTS "--reverse --bind=ctrl-z:ignore $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS"
    eval "$FZF_CTRL_T_COMMAND | fzf"' -m --query "'$fzf_query'"' | while read -l r; set result $result $r; end
  end
  if [ -z "$result" ]
    commandline -f repaint
    return
  else
    # Remove last token from commandline.
    commandline -t ""
  end

  for i in $result
    commandline -it -- $prefix
    commandline -it -- (string escape $i)
    commandline -it -- ' '
  end
  commandline -f repaint
end
