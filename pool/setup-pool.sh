#!/usr/bin/env bash
# Registers two GitHub Actions runner instances on a freshly-booted pool VM
# (provisioned by cloud-init.yaml) as long-lived, non-ephemeral, org-level
# runners, then starts them as systemd services.
#
# Run over SSH from hetzner-pool-recycle.yml, which holds the secrets this
# script needs — never commit a filled-in copy of this with real values.
#
# Required environment:
#   RUNNER_PAT    Classic GitHub PAT with the admin:org scope (fine-grained
#                 PATs don't support org-level runner registration at all —
#                 see docs/hetzner-pool.md "Secrets" for why)
#   RUNNER_LABEL  label callers use in runs-on:, e.g. "promptics-pool"
#   POOL_NAME     name prefix for this VM's two runner registrations,
#                 e.g. "hetzner-pool-01" -> hetzner-pool-01-a / -b

set -euo pipefail

: "${RUNNER_PAT:?RUNNER_PAT is required}"
: "${RUNNER_LABEL:?RUNNER_LABEL is required}"
: "${POOL_NAME:?POOL_NAME is required}"

ORG=promptics

for slot_num in 1 2; do
  suffix=$([ "$slot_num" = "1" ] && echo "a" || echo "b")
  dir="/opt/actions-runner-${slot_num}"
  name="${POOL_NAME}-${suffix}"
  # Each slot runs as its own Linux user (runner-a / runner-b), each with
  # its own $HOME -- see cloud-init.yaml for why: sharing one "runner"
  # user let two concurrent jobs race on the same pnpm/npm cache path and
  # corrupt each other's install.
  user="runner-${suffix}"

  echo "== Registering ${name} in ${dir} as ${user} =="

  # Mint a fresh org-level registration token (valid ~1 hour, single use).
  reg_token=$(curl -fsSL -X POST \
    -H "Authorization: token ${RUNNER_PAT}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/orgs/${ORG}/actions/runners/registration-token" \
    | jq -r '.token')

  sudo -u "$user" bash -c "
    cd '${dir}'
    ./config.sh \
      --url 'https://github.com/${ORG}' \
      --token '${reg_token}' \
      --name '${name}' \
      --labels '${RUNNER_LABEL},linux,x64' \
      --work '_work' \
      --unattended \
      --replace
  "

  # Install + start as a systemd service (svc.sh ships in the runner
  # tarball; the argument is which Linux user the service runs as).
  (cd "$dir" && ./svc.sh install "$user" && ./svc.sh start)

  echo "== ${name} registered and running as ${user} =="
done

echo "Pool VM ready: 2 runner slots, label=${RUNNER_LABEL}"
