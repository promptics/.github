# Hetzner runner pool

Org-wide alternative to `runs-on: ubuntu-latest` for short, frequent,
highly parallel CI jobs — the shape that's actually driving promptics'
GitHub Actions spend (see "Why a pool, not the ephemeral pattern" below).

## Quick start (downstream project)

Change the runner on the jobs you're moving:

```yaml
jobs:
  unit:
    runs-on: [self-hosted, promptics-pool]
    steps: [...]
```

That's the entire per-project change — no new jobs, no secrets, no `uses:`
of a reusable workflow. The pool is always on, like a self-owned
GitHub-hosted runner. Two things worth doing alongside the label swap:

1. **Non-idempotent jobs**: the pool VM does not wipe state between jobs
   the way a fresh ephemeral VM would — two jobs from different PRs can see
   each other's leftover `_work` files. Testcontainers-based tests are fine
   (ephemeral containers). Anything that writes to a shared local path
   should add a `container:` key to isolate it:
   ```yaml
   jobs:
     unit:
       runs-on: [self-hosted, promptics-pool]
       container: eclipse-temurin:21-jdk
       steps: [...]
   ```
2. **macOS jobs cannot move here** — Hetzner Cloud has no macOS offering.
   Leave those on `runs-on: macos-14` etc.

Or pick the **"Hetzner pool job"** template from Actions → New workflow →
"By promptics".

## Why a pool, not the ephemeral pattern

promptLM's `.github` repo runs a proven **ephemeral** Hetzner pattern:
provision a VM per workflow run, execute, tear down
(`promptLM/.github/docs/hetzner-runners.md`). It's the right fit for their
use case — a single long acceptance suite per run.

promptics' cost driver looks structurally different: a small number of
repos firing many short, parallel jobs per push (one workflow fans out to
13+ parallel `ubuntu-latest` jobs on every push; another fires dozens of
times a day on `push` triggers alone). Provisioning a fresh VM per *job* at
that volume means paying Hetzner's hourly-rounded rate once per job plus
`ubuntu-latest` provision/teardown overhead on top of each one — plausibly
*more* expensive than the status quo, not less.

A **persistent pool** — a small number of always-on runner slots,
recycled weekly rather than per-run — amortizes one flat VM cost across
unlimited job-minutes instead. Cost stops scaling with commit volume.

**Use the pool for:** unit tests, lint, fast/frequent gates, anything
firing more than a few times an hour or under ~4 minutes per job.
**Use promptLM's ephemeral pattern for:** long (20+ min), infrequent jobs —
see their docs, and pass promptics' own `HCLOUD_TOKEN`/`RUNNER_PAT`
explicitly rather than `secrets: inherit` since it's a cross-org call.

## Why not share promptLM's setup

The two patterns need different infrastructure (always-on pool vs.
create/destroy per run), so there's no actual code or running
infrastructure to share by pointing promptics at promptLM's Hetzner
project — only the *design* is shared (this doc, and the toolchain list
below, both intentionally mirroring promptLM's proven recipe). Keeping
separate Hetzner Cloud projects/tokens per org means a compromised or
misconfigured job in one org's repos can't touch the other org's runner
fleet or Hetzner billing/quota, and creating a second Hetzner project costs
nothing.

## What lives where

| File | Role |
|---|---|
| `.github/workflows/hetzner-pool-recycle.yml` | Weekly (Monday 04:00 UTC) + manual: boots a fresh pool VM, registers two runner slots, retires the previous VM. |
| `pool/cloud-init.yaml` | Base OS provisioning (no secrets) — Ubuntu 24.04 + Docker + JDK 17/21 + Node 22 + Maven/Gradle, same toolchain promptLM's snapshot bakes, plus `shellcheck`/`locales` and passwordless `sudo` for the `runner` user (see "Missing tools" below). |
| `pool/setup-pool.sh` | Runs over SSH from the recycle workflow (needs `RUNNER_PAT`): registers the two org-level runner slots as systemd services. |
| `workflow-templates/hetzner-pool.yml` | Starter template in the "New workflow" picker. |

No nightly snapshot bake is needed here (unlike promptLM's platform) — the
pool VM boots once per week via `cloud-init.yaml` instead of once per run,
so there's nothing to pre-bake for speed.

## One-time setup (admin)

**Repository-level, not org-level.** The `promptics` org is on GitHub
Free, which doesn't offer organization secrets/variables at all (that's a
Team/Enterprise feature) — but that turns out not to cost this design
anything: the recycle workflow in *this* repo is the only thing that ever
touches `HCLOUD_TOKEN`, `RUNNER_PAT`, or the SSH key name. No caller repo
(`agentskills`, `promptics-speech`, ...) needs any secret at all — they
only ever reference the `promptics-pool` runner label. So everything below
is a plain **repository secret/variable on `promptics/.github`**, which
works on every GitHub plan.

### Secrets

Under `https://github.com/promptics/.github/settings/secrets/actions`
(**Repository secrets**, not the org-level page):

| Secret | Source |
|---|---|
| `HCLOUD_TOKEN` | A **separate** Hetzner Cloud project (don't reuse promptLM's) → Security → API Tokens (Read & Write) |
| `RUNNER_PAT` | GitHub → **classic** PAT (`github.com/settings/tokens/new`) with the **`admin:org`** scope. |

**Why classic, not fine-grained.** Fine-grained PATs don't expose
org-level self-hosted-runner management at all — there's no "Self-hosted
runners" entry under Organization permissions to pick, at any scope. Only
two things can mint/delete an org runner-registration token:
a classic PAT with `admin:org`, or a GitHub App with the
`organization_self_hosted_runners` permission.

`admin:org` is broader than strictly needed — it also covers org
membership, teams, and webhooks, not just runners. The narrower option is
a **fine-grained** PAT with **Administration: Read/write** scoped to just
`agentskills` + `promptics-speech` — but that only supports **repo-level**
runner registration, meaning each pool slot would have to be permanently
assigned to one specific repo instead of shared. That breaks the actual
point of pooling for `promptics-speech` (its 13-job-per-push fan-out
needs several slots available *to it* at once, not one slot it can never
borrow from). Going with `admin:org` to keep slots shared across repos;
revisit with a GitHub App (see promptLM's own "Roadmap / known limits" —
they deferred the same migration) if the broader scope becomes a concern.

### Admin SSH access (optional but recommended)

The recycle workflow generates its own throwaway SSH key each run (create,
use, delete) — that key is gone by the time the run finishes, so it doesn't
give a human any lasting way in. To be able to SSH into the pool VM
yourself later (the "SSH in and check `systemctl status`" step under
Troubleshooting), add your own key once:

1. Hetzner Console → your project → Security → SSH Keys → add your public
   key, give it a name.
2. Set that name as a **repository variable** (not secret — it's just a
   name) on `promptics/.github`, under
   `https://github.com/promptics/.github/settings/variables/actions`:
   `HETZNER_ADMIN_SSH_KEY_NAME`.

Every pool VM the recycle workflow creates will then carry both keys —
the automation's own (deleted after each run) and yours (persists). Skip
this and the pool still works fine; you just can't SSH in without adding
this later.

### Runner group

Under `https://github.com/organizations/promptics/settings/actions/runner-groups`:
restrict the group the pool's runners land in to the repos that should use
it, starting with `agentskills` and `promptics-speech`. These are private
repos with no fork-PR traffic, which is what makes a standing (non-ephemeral)
runner an acceptable risk here — don't add this group to a public repo or
one building fork PRs without also adding fork-PR sandboxing.

### First boot

Actions tab (this repo) → "Hetzner pool recycle" → Run workflow. Takes
~5-8 minutes (no pre-baked snapshot). Confirm two runners named
`hetzner-pool-<timestamp>-a` / `-b` appear at
`https://github.com/organizations/promptics/settings/actions/runners`,
both idle/online. It then recycles itself weekly on its own.

## Sizing

Starts at **2 concurrent slots on one `cx33`** (4 vCPU/8 GB — same spec
promptLM validated in production, ~€6.49/mo flat). A 13-job fan-out will
queue behind 2 slots rather than run all at once initially — that's fine
(GitHub queues, doesn't fail), but watch queue times after onboarding a
repo.

To scale:
- **More slots, same VM**: `cx33` → `cx43` (8 vCPU/16 GB, ~€13-14/mo),
  add a 3rd/4th `actions-runner-N` directory in `cloud-init.yaml` and a
  matching iteration in `setup-pool.sh`'s loop.
- **More VMs**: run the create step in `hetzner-pool-recycle.yml` twice
  with different `POOL_NAME`s — only worth it if CPU, not job count,
  becomes the bottleneck.

Check current usage:
`gh api orgs/promptics/actions/runners --paginate -q '.runners[] | {name,status,busy}'`.

## Cost model

| Server type | Monthly cap | Slots |
|---|---|---|
| `cx33` (default) | ~€6.49 | 2 |
| `cx43` | ~€13-14 | 3-4 |

Flat regardless of job volume or push frequency — the point of the pool.

## Troubleshooting

**A job fails on a missing tool / `sudo: command not found` / a package
GitHub-hosted images ship that this one doesn't.** Expected occasionally —
GitHub's `ubuntu-latest` image bundles hundreds of preinstalled tools
(see [actions/runner-images](https://github.com/actions/runner-images)),
and `cloud-init.yaml` only bakes in what promptics' actual workflows are
known to need so far (found by porting `agentskills`' `gates.yml` —
needed `shellcheck` — and `heavy-gates.yml` — needed `sudo locale-gen`,
which needs `sudo` itself). The `runner` user has passwordless `sudo`
specifically so a job can self-heal with an `apt-get install -y <tool>`
step rather than blocking on a cloud-init PR; add the package to
`cloud-init.yaml`'s `packages:` list too if it's going to recur across
jobs.

**A job stays queued.** Both slots busy — check with the `gh api` command
above. If routine, scale per "Sizing".

**A runner shows offline and stays that way.** Something crashed on the VM
without systemd noticing. SSH in (`hcloud server ip hetzner-pool-<ts>`),
check `systemctl status actions.runner.*`. If it won't recover, just
trigger the recycle workflow manually — it's idempotent.

**Two jobs interfere with each other.** Expected risk of a non-ephemeral
runner — add `container:` to isolate, or make one slot `--ephemeral` in
`setup-pool.sh` if this becomes routine (loses zero-latency for that slot).
Observed once during the `promptics-speech` load test: a `pnpm: command
not found` on a step after `pnpm/action-setup` had just run successfully
earlier in the same job, on a slot that had run several other jobs
back-to-back — looked like PATH state from `$GITHUB_PATH` not resetting
cleanly between jobs on the same slot. Single occurrence out of 18 jobs;
treat a recurrence as a signal to isolate that specific job with
`container:` rather than something to chase further speculatively.

**Recycle fails at "Register runner slots."** Almost always `RUNNER_PAT`.
Confirm it's a **classic** PAT with `admin:org` — a fine-grained PAT
produces a 403/404 on the registration-token call because org-level
runner management isn't exposed to fine-grained PATs at all, regardless
of what permissions you pick. (promptLM's ephemeral pattern uses a
fine-grained PAT with repo-level `Administration` instead — that works
for *their* repo-level registration, a different mechanism entirely.
Don't copy their PAT setup verbatim for this workflow.)

**Two pool VMs billing simultaneously.** The recycle workflow deletes the
previous VM only after the new one registers successfully — a mid-run
failure can leave both up (~€13/mo instead of ~€6.49, not catastrophic).
`hcloud server list` and delete the stale one. There's no daily orphan
sweep here yet the way promptLM has one for their ephemeral VMs — worth
adding if this recurs.

## Source

Researched 2026-09-18 by querying the GitHub Actions billing-usage API
directly for both the `promptics` and `promptLM` orgs (`gh api
"orgs/<org>/settings/billing/usage"`) rather than assuming spend — see the
originating PR description for the full evidence and the ephemeral-vs-pool
decision reasoning. The base toolchain and the `HCLOUD_TOKEN`/`RUNNER_PAT`
naming convention are deliberately copied from promptLM's proven platform;
the pool architecture itself is new. Cyclenerd's action is not used here
(the pool registers runners directly via `config.sh`/`svc.sh`, since it's
managing standing runners, not create/destroy-per-run) — see
[actions/runner](https://github.com/actions/runner) (MIT) for the binary
this platform installs.
