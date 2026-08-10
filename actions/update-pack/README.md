# Update Nomad Pack

Update one `nomad-packs` moving channel after an image or OCI artifact tag is deployable.

The Action owns Pack dispatch authentication, stale-branch protection, input validation, and the
mapping from `mode` to immutable Pack tag creation. It does not build, publish, sync, or deploy the
artifact and it does not interpret source branch naming conventions.

See the repository [README](../../README.md) for the contract and examples.
