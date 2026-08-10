# Publish Pack-backed Docker application

Internal composite implementation for the public
`.github/workflows/publish-pack-docker.yml` reusable workflow.

It handles the Orchestra-style `dev`, selected `release/vX.Y.Z`, formal `vX.Y.Z`, and manual-build
protocol. Direct use is supported for custom callers, but the reusable workflow is preferred
because it provides the job, concurrency, permissions, organization variables, and inherited
secret interface.

The build convention is fixed to `./Dockerfile`, target `runtime`, and `linux/amd64`. Applications
with custom runners or build graphs should keep their own workflow and compose `acr-sync` plus
`actions/update-pack` after publication.
