# Publish Docker Package

Build and optionally publish one `linux/amd64` Docker package to GHCR.

The caller supplies an explicit GHCR `package` and newline-delimited Docker `tags`. Tags contain
only values such as `v1.2.3` or `dev` and must not repeat the registry, owner, or package. The Action derives the lowercase namespace from `github.repository_owner` and
returns the complete image name, references, and published digest.

```yaml
- id: docker
  uses: Qiyin-Tech/publish-actions/actions/publish-docker@v1
  with:
    package: orchestra-backend
    tags: |
      dev-v1.2.3-0123456789abcdef
      dev
    context: .
    file: ./Dockerfile
    target: runtime
    cache_from: type=registry,ref=ghcr.io/qiyin-tech/orchestra-backend:dev
    cache_to: type=inline
    push: true
    token: ${{ github.token }}
```

The implementation is intentionally fixed to `linux/amd64`. It does not inspect Git refs, classify
dev/RC/releases, synchronize ACR, create GitHub Releases, or update Nomad Packs.
