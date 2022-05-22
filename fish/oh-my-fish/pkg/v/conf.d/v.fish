if type -q nvim
  function v
    set -l file (nvim -e -u NONE --headless +oldfiles +qall 2>&1 | cut -d ' ' -f2- | xargs -d '\n' -P1 -n1 fish -N -c 'set -l file (string trim $argv[1]); if test -f $file; echo $file; end' | fzf -1 -0 --no-sort +m)

    if [ (echo $file) ]
      $EDITOR $file
    end
  end
end
