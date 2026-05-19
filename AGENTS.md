# AGENTS.md

### `manage`

non-obvious guidance for coding agents working on the root `manage` CLI. Do not treat it as a repo overview or command reference.

### Critical non-obvious constraints
- Keep `manage` self-contained at runtime: Python standard library only. `uv`, ruff, ty, and lockfiles are for development checks, not production install behavior.
- Treat `TOOL_CONFIGS` as the single source of truth for managed tools. Do not reintroduce scattered per-tool constants, or tool-specific install branches when metadata can express the behavior.
- GitHub access is intentionally unauthenticated. Do not depend on `gh`, stored credentials, `GH_TOKEN`, or `GITHUB_TOKEN` for runtime verification or downloads.
- Minimize GitHub API calls. Prefer deterministic release download URLs for assets, avoid proactive rate-limit polling, and keep signature checks expectation-driven.
- Keep tag-signature and commit-signature policy separate. Signed annotated tags may be the release trust anchor even when the target commit is unsigned.
- Archive handling must stay generic. Use metadata such as `install_layout`, binary source paths, and `strip_components`; do not add one-off extraction code for tools such as `nvim`.

### Known landmines and misleading patterns
- `gruntwork-io/fetch` uses GitHub API calls for release asset downloads and fails immediately on unauthenticated rate limits. Do not route managed asset downloads through fetch unless that tradeoff is explicitly revisited.
- A locally valid tag may be a lightweight tag, a signed annotated tag, or an unsigned annotated tag. Do not infer one signature policy from another.
- `strip_components` applies before locating binaries or preserving archive trees; binary source paths are relative to the post-strip tree.

### Ask before doing
- Ask before running network-heavy installs such as default `./manage install`; unauthenticated GitHub API limits are easy to exhaust.
- Ask before changing canonical home-directory behavior under `$HOME/.dotfiles`, runcom linking, fish backup behavior, or context-engineering clone behavior.

## Maintenance note
- Remove lines from this file once the underlying constraint is enforced clearly enough in code, tests, CI, comments, or structure.
