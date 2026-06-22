# In conf.d, pi.fish loads after nodenv.fish alphabetically here, so that specific
# concern is not meaningful in this repo layout.
if test -d $HOME/.pi/agent; and type -P pi >/dev/null 2>/dev/null
  function pi --wraps pi --description 'Run pi with local pi overrides'
    set -l env_args PI_TELEMETRY=false

    if test -d $HOME/.pi/agent/npm/node_modules/@ff-labs/pi-fff
      set -a env_args PI_FFF_MODE=override
    else
      set -p env_args -u PI_FFF_MODE
    end

    env $env_args command pi $argv
  end
end
