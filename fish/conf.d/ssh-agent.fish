if ! test -S $SSH_AUTH_SOCK
  if test -f $HOME/.ssh/environment
    set -xg SSH_ENV $HOME/.ssh/environment
  end

  if not __ssh_agent_is_started
    __ssh_agent_start
  end
end
