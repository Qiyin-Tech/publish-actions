# publish-actions

Reusable GitHub Actions and workflows for Qiyin-Tech application publishing.

This repository is public by design. It contains no credentials: callers provide registry and
GitHub App credentials through their own Actions variables and secrets.

## Boundaries

The repository owns publishing protocol, not application-specific builds:

- `actions/publish-docker` builds and publishes a conventional `linux/amd64` image to GHCR;
- [`acr-sync`](https://github.com/Qiyin-Tech/acr-sync) remains the authority for copying that image
  or another OCI artifact to ACR;
- `actions/update-pack` updates a Nomad Pack channel after the deployable version is available;
- `.github/workflows/publish-docker.yml` composes those three protocols for conventional
  Pack-backed Docker applications;
- custom Windows, OCI artifact, GPU, cache, or deploy-asset workflows stay in their application
  repositories and compose only the narrow actions they need.

GitHub ref rules belong to adapters. `update-pack` receives a normalized plan and does not know
whether a caller uses `main`, `dev`, `release/**`, or another branch convention.

## Standard Pack-backed Docker workflow

A caller retains only triggers and permissions:

```yaml
name: Publish application

on:
  push:
    branches: [dev, 'release/**']
    tags: ['v*.*.*']
  workflow_dispatch:

permissions:
  contents: write
  packages: write

jobs:
  publish:
    uses: Qiyin-Tech/publish-actions/.github/workflows/publish-docker.yml@v1
    with:
      pack: orchestra-frontend
      rc_branch: ${{ vars.RC_BRANCH }}
      build_args: |
        VITE_API_BASE_PATH=/v1
      cache_mode: registry
      cache_tag: buildcache
    secrets: inherit
```

The workflow expects caller variables `ACR_ENDPOINT` and `ACR_USERNAME`, plus secrets
`ACR_PASSWORD`, `NOMAD_PACKS_APP_CLIENT_ID`, and `NOMAD_PACKS_APP_PRIVATE_KEY`.

Its ref contract is:

| Source ref | Image tags | Pack update |
|---|---|---|
| `dev` | `dev`, `dev-<nearest-vX.Y.Z>-<sha>` | moving `dev` |
| selected `release/vX.Y.Z` | `rc`, `rc-vX.Y.Z-<sha>` | moving `rc` |
| strict `vX.Y.Z` tag | `vX.Y.Z` | `dev` plus immutable `<pack>/vX.Y.Z` tag |
| `workflow_dispatch` | local `manual-<sha>` build only | none |

The Docker convention is intentionally fixed to `context=.`, `file=./Dockerfile`,
`target=runtime`, and `platform=linux/amd64`. A repository that cannot follow this convention keeps
its own build workflow and composes `acr-sync` and `update-pack` itself.

`actions/publish-docker` deliberately has no ACR or Nomad Pack credentials. The reusable workflow
uses its normalized outputs to invoke `acr-sync`, create a formal GitHub Release when applicable,
and finally invoke `update-pack`.

## Update one Pack

`actions/update-pack` accepts caller-owned Pack identity and an already-published version:

```yaml
- name: Update release Pack
  uses: Qiyin-Tech/publish-actions/actions/update-pack@v1
  with:
    pack: svc
    version: v0.1.0
    channel: dev
    mode: release
    app_client_id: ${{ secrets.NOMAD_PACKS_APP_CLIENT_ID }}
    app_private_key: ${{ secrets.NOMAD_PACKS_APP_PRIVATE_KEY }}
```

Inputs:

| Input | Required | Meaning |
|---|---:|---|
| `pack` | yes | Exact directory under `nomad-packs/packs`; never inferred |
| `version` | yes | Published image or artifact tag written into the Pack |
| `channel` | yes | Moving Pack branch, currently `dev` or `rc` |
| `mode` | yes | `moving` updates the branch; `release` also creates an immutable Pack tag |
| `guard_ref` | no | Source branch that must still point to `github.sha` |
| `app_client_id` | yes | GitHub App capability used only to dispatch `nomad-packs` |
| `app_private_key` | yes | Matching GitHub App private key |

The Action intentionally has no image/artifact input. Publication and ACR synchronization must
succeed before it runs; it only links a deployable version into the Pack registry.

## Versioning

All actions and reusable workflows use one repository-wide compatibility line. Callers use the
moving major tag `@v1`; security- or reproducibility-sensitive callers may pin an exact commit SHA.
Internal composition uses GitHub's `$/...` self-repository syntax, so nested Actions resolve from the
same exact commit as the selected reusable workflow instead of falling back to a moving tag.
Breaking interface changes require `v2`.
