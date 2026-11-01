if ! test -S "$SSH_AUTH_SOCK"
  set -xg SSH_ENV "$HOME/.ssh/environment"

  if not __ssh_agent_is_started
    __ssh_agent_start
  end
end
