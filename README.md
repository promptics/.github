# promptics / .github

Org-wide GitHub assets for the [promptics](https://github.com/promptics)
organization: reusable workflows and org-default community files
(`profile/README.md`).

## Reusable workflows

| Workflow | Used by | Purpose |
|---|---|---|
| [`hetzner-pool-recycle.yml`](.github/workflows/hetzner-pool-recycle.yml) | The pool platform itself (scheduled) | Weekly recycle of the always-on Hetzner runner pool |

### Hetzner runner pool

Alternative to `ubuntu-latest` for short, frequent, parallel CI jobs — a
small always-on Hetzner runner pool instead of a per-run VM. Downstream
usage is a one-line label change:

```yaml
jobs:
  unit:
    runs-on: [self-hosted, promptics-pool]
    steps: [...]
```

Full setup, cost math, sizing, and troubleshooting:
[`docs/hetzner-pool.md`](docs/hetzner-pool.md). For new workflows, pick the
**"Hetzner pool job"** template under Actions → New workflow.

For long-running jobs (20+ min acceptance/integration suites), use
[promptLM/.github's ephemeral Hetzner pattern](https://github.com/promptLM/.github#hetzner-runner-platform)
instead — it's a public reusable workflow, callable cross-org, and already
proven in production. See `docs/hetzner-pool.md`'s "Why a pool, not the
ephemeral pattern" for when to use which.

## Profile

[`profile/README.md`](profile/README.md) is rendered at the top of the
[organization page](https://github.com/promptics) for unauthenticated
visitors.
