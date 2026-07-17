# tools_local SELinux module

Purpose: run selected `manage` CLI tools and their children in a local domain with broad local filesystem access, no `sudo` allowances, and true offline behavior.

Covered tools:
- `fzf`
- `fd`
- `hunk` (with its session daemon disabled)
- `difft`
- `zoxide`
- `walk`
- `fx`
- `gdu`
- `tokei`
- `svu`
- `shellcheck`
- `stylua`
- `actionlint`
- `harper`
- `harper-ls`
- `lua-language-server`
- `tree-sitter`
- `zizmor`

Source files:
- `tools_local.te`
- `tools_local.fc`

Policy vs local configuration:

- `tools_local.te` defines the domain, transitions, and permissions.
- `tools_local.fc` is intentionally path-free.
- The binary path labels are local machine configuration, installed with `semanage fcontext`, because the real paths depend on the current `$HOME` and should not be hard-coded in policy.

This split follows normal SELinux practice for non-standard local paths: keep policy in the module, and keep host-specific file-context mappings in local SELinux configuration.

Build:

```bash
make -f /usr/share/selinux/devel/Makefile tools_local.pp
```

Generated artifacts:

- `tmp/`
- `tools_local.pp`
- `tools_local.if`

These are build outputs from the SELinux development Makefile. The build system hard-codes `tmp/`, so the directory name is expected rather than project-specific.

Install:

```bash
sudo semodule -i tools_local.pp
sudo semanage fcontext -a -t tools_local_exec_t "$HOME/.dotfiles/(bin/lua-language-server|vendor/(fzf/fzf|fd/fd|hunk/hunk|difft/difft|zoxide/zoxide|walk/walk|fx/fx|gdu/gdu|tokei/tokei|svu/svu|shellcheck/shellcheck|stylua/stylua|actionlint/actionlint|harper/harper|harper-ls/harper-ls|lua-language-server/bin/lua-language-server|tree-sitter/tree-sitter|zizmor/zizmor))"
for tool in fzf fd hunk difft zoxide walk fx gdu tokei svu shellcheck stylua actionlint harper harper-ls lua-language-server tree-sitter zizmor; do
  if [ -d "$HOME/.dotfiles/vendor/$tool" ]; then
    sudo restorecon -RFv "$HOME/.dotfiles/vendor/$tool"
  fi
done
```

The explicit `semanage fcontext` entry is needed because the binaries live under a home-directory path, where the generic home labeling rules otherwise win. This is intentional local configuration, not a policy-source concern.

The regex targets the expected managed entrypoint path for each covered tool. Most tools use `vendor/<tool>/<tool>`. `lua-language-server` also includes the `bin/lua-language-server` wrapper entrypoint because that wrapper is what users normally execute. Hunk runs through its normal symlink; Git's pager command and the Fish environment set `HUNK_MCP_DISABLE=1`, so it does not start or connect to the local session daemon.

Run `restorecon` after installing a newly covered tool.

Uninstall:

```bash
sudo semodule -r tools_local
sudo semanage fcontext -d "$HOME/.dotfiles/(bin/lua-language-server|vendor/(fzf/fzf|fd/fd|hunk/hunk|difft/difft|zoxide/zoxide|walk/walk|fx/fx|gdu/gdu|tokei/tokei|svu/svu|shellcheck/shellcheck|stylua/stylua|actionlint/actionlint|harper/harper|harper-ls/harper-ls|lua-language-server/bin/lua-language-server|tree-sitter/tree-sitter|zizmor/zizmor))"
for tool in fzf fd hunk difft zoxide walk fx gdu tokei svu shellcheck stylua actionlint harper harper-ls lua-language-server tree-sitter zizmor; do
  if [ -d "$HOME/.dotfiles/vendor/$tool" ]; then
    sudo restorecon -RFv "$HOME/.dotfiles/vendor/$tool"
  fi
done
```

This removes the module, deletes the persistent file-context override, and restores covered binaries to the default home-directory labels.

If the same local path mapping needs to be reproduced on another machine, prefer exporting and importing the verified `semanage` configuration rather than encoding user-specific paths into the policy module.

Check:

```bash
ps -eZ | grep tools_local
sudo ausearch -m AVC -ts recent -se tools_local_t
```

The module is intended for user-level CLI tools. It keeps child processes inside `tools_local_t`, allows practical local filesystem access, and intentionally omits the `sudo`-specific allowances that `nvim_local_t` needed.

Network access remains blocked for both TCP and UDP. The policy intentionally omits SELinux networking allow macros. Expected blocked HTTP connect attempts and UDP socket creation are `dontaudit`ed to keep audit logs quieter.

If debugging is needed later, temporarily disable `dontaudit` rules, reproduce the problem, then restore them:

```bash
sudo semodule -DB
# reproduce the scenario
sudo ausearch -m AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR -ts recent -se tools_local_t
sudo semodule -B
```
