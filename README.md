# publish-actions

Composable GitHub Actions for Qiyin-Tech application publishing.

This repository is public and contains no credentials. All Action parameters are declared as named
inputs; sensitive values are supplied to those inputs from the caller's GitHub Secrets.

## Actions

### `actions/publish-docker`

Owns only GHCR reference construction, login, Buildx setup, and Docker build-push. The caller
supplies an explicit package, plain Docker tags, publication token, push choice, build definition,
and cache configuration. It does not inspect refs, version conventions, RC branches, ACR,
Releases, or Packs. Version 1 builds only `linux/amd64`.

### `actions/update-pack`

Creates a short-lived `nomad-packs` GitHub App token, skips a stale source-branch run, and dispatches
one Pack update. Inputs are:

| Input | Required | Meaning |
|---|---:|---|
| `app_client_id` | yes | Non-secret GitHub App client ID |
| `app_private_key` | yes | GitHub App private key; supply from GitHub Secrets |
| `pack` | yes | Exact Pack directory name |
| `version` | yes | Published image or artifact version |
| `branch` | yes | Pack channel (`dev`, `test`, or `rc`); nomad-packs writes `<pack>/<channel>` |
| `tag` | no | When true, create `<pack>/<version>` on the updated commit |

[`Qiyin-Tech/acr-sync`](https://github.com/Qiyin-Tech/acr-sync) remains the independent authority
for GHCR-to-ACR synchronization.

## Composition example

```yaml
permissions:
  contents: write
  packages: write

steps:
  - uses: actions/checkout@v7

  # The caller owns ref classification and version naming.
  - id: metadata
    shell: bash
    run: bash .github/scripts/resolve-publish-metadata.sh

  - id: docker
    uses: Qiyin-Tech/publish-actions/actions/publish-docker@v1
    with:
      package: example-app
      tags: ${{ steps.metadata.outputs.docker_tags }}
      push: ${{ github.event_name != 'workflow_dispatch' }}
      token: ${{ github.token }}

  - if: ${{ github.event_name != 'workflow_dispatch' }}
    uses: Qiyin-Tech/acr-sync@v2
    with:
      source: ${{ steps.docker.outputs.image }}
      tag: ${{ steps.metadata.outputs.version }}
      arch: amd64
      target_namespace: qiyin
      source_username: ${{ github.actor }}
      source_password: ${{ github.token }}
      acr_endpoint: ${{ vars.ACR_ENDPOINT }}
      acr_username: ${{ vars.ACR_USERNAME }}
      acr_password: ${{ secrets.ACR_PASSWORD }}

  - if: ${{ github.event_name != 'workflow_dispatch' }}
    uses: Qiyin-Tech/publish-actions/actions/update-pack@v1
    with:
      app_client_id: ${{ vars.NOMAD_PACKS_APP_CLIENT_ID }}
      app_private_key: ${{ secrets.NOMAD_PACKS_APP_PRIVATE_KEY }}
      pack: example-app
      version: ${{ steps.metadata.outputs.version }}
      branch: ${{ steps.metadata.outputs.pack_branch }}
      tag: ${{ github.ref_type == 'tag' }}
```

Repository workflows retain their triggers, concurrency, timeout, Docker cache/build arguments,
ACR target, and complete GitHub Release behavior while avoiding duplication in the shared
publication protocols.

## Versioning

All Actions share one moving major compatibility tag, `@v1`. Security- or reproducibility-sensitive
callers may pin an exact commit SHA. Breaking interfaces require `v2`.
