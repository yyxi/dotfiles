function j -d "Change directory"
  set -l commandline (__fzf_parse_commandline)
  set -l dir $commandline[1]
  set -l fzf_query $commandline[2]
  set -l prefix $commandline[3]

  # set -l FZF_ALT_C_COMMAND "
  # command find -L \$dir -mindepth 1 \\( -path \$dir'*/\\.*' -o -fstype 'sysfs' -o -fstype 'devfs' -o -fstype 'devtmpfs' \\) -prune \
  # -o -type d -print 2> /dev/null | sed 's@^\./@@'"

  set -l FZF_ALT_C_COMMAND "command fd -L -H --min-depth 1 --type d \$dir 2> /dev/null"

  begin
    set -lx FZF_DEFAULT_OPTS "--reverse --bind=ctrl-z:ignore $FZF_DEFAULT_OPTS"

    eval "$FZF_ALT_C_COMMAND | fzf"' +m --query "'$fzf_query'"' | read -l result

    if [ -n "$result" ]
      cd -- $result

      # Remove last token from commandline.
      commandline -t ""
      commandline -it -- $prefix
    end
  end

  commandline -f repaint
end
