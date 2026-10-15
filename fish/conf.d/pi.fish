# In conf.d, pi.fish loads after nodenv.fish alphabetically here, so that specific
# concern is not meaningful in this repo layout.
if test -d $HOME/.pi/agent; and type -P pi >/dev/null 2>/dev/null
  function pi --wraps pi --description 'Run pi with local pi overrides'
    set -l env_args PI_TELEMETRY=false

    env $env_args command pi $argv
  end
end
