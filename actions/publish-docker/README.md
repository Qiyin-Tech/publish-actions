# Publish Docker

Build and publish a conventional `linux/amd64` Docker image to GHCR.

The Action handles the Orchestra-style `dev`, selected `release/vX.Y.Z`, strict `vX.Y.Z`, and
manual-build ref protocol. It publishes immutable tags first, verifies moving refs before and after
the build, and only then updates the `dev` or `rc` GHCR tag.

It deliberately has no ACR credentials, Nomad Pack identity, or Pack GitHub App credentials. Its
`image`, `image_tag`, `kind`, and `published` outputs let a caller independently compose
`Qiyin-Tech/acr-sync` and `actions/update-pack`.

The build convention is fixed to `./Dockerfile`, target `runtime`, and `linux/amd64`. Applications
with custom runners or build graphs should keep their own build workflow.
