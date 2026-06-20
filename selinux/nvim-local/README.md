# nvim_local SELinux module

Purpose: run Neovim and its children in a local domain with explicit local-only access and true offline behavior.

Source files:
- `nvim_local.te`
- `nvim_local.fc`

Policy vs local configuration:

- `nvim_local.te` defines the domain, transitions, and permissions.
- `nvim_local.fc` is intentionally path-free.
- The binary path label is local machine configuration, installed with `semanage fcontext`, because the real path depends on the current `$HOME` and should not be hard-coded in policy.

This split follows normal SELinux practice for non-standard local paths: keep policy in the module, and keep host-specific file-context mappings in local SELinux configuration.

Build:

```bash
make -f /usr/share/selinux/devel/Makefile nvim_local.pp
```

Generated artifacts:

- `tmp/`
- `nvim_local.pp`
- `nvim_local.if`

These are build outputs from the SELinux development Makefile. The build system hard-codes `tmp/`, so the directory name is expected rather than project-specific.

Install:

```bash
sudo semodule -i nvim_local.pp
sudo semanage fcontext -a -t nvim_local_exec_t "$HOME/.dotfiles/vendor/nvim/bin/nvim"
sudo restorecon -v "$HOME/.dotfiles/vendor/nvim/bin/nvim"
```

The explicit `semanage fcontext` entry is needed because the binary lives under a home-directory path, where the generic home labeling rules otherwise win. This is intentional local configuration, not a policy-source concern.

Uninstall:

```bash
sudo semodule -r nvim_local
sudo semanage fcontext -d "$HOME/.dotfiles/vendor/nvim/bin/nvim"
sudo restorecon -v "$HOME/.dotfiles/vendor/nvim/bin/nvim"
```

This removes the module, deletes the persistent file-context override, and restores the binary to the default home-directory label.

If the same local path mapping needs to be reproduced on another machine, prefer exporting and importing the verified `semanage` configuration rather than encoding user-specific paths into the policy module.

Check:

```bash
ps -eZ | grep nvim
sudo ausearch -m AVC -ts recent -se nvim_local_t
```

The module is now enforced. A local `execmem` allow was needed for Neovim's Lua runtime code generation, and the policy now uses explicit home, tmp, exec, and terminal macros instead of the earlier broad unconfined-style grants. `sudo` still works inside `nvim_local_t`.

Network access remains blocked for both TCP and UDP. The policy intentionally omits SELinux networking allow macros, and UDP socket creation is denied. Expected outbound web `name_connect` denials to `http_port_t` are `dontaudit`ed to keep audit logs quieter.

If debugging is needed later, temporarily disable `dontaudit` rules, reproduce the problem, then restore them:

```bash
sudo semodule -DB
# reproduce the scenario
sudo ausearch -m AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR -ts recent -se nvim_local_t
sudo semodule -B
```
