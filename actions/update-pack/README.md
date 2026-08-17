# Update Nomad Pack

Update one `<pack>/<dev|test|rc>` channel after an image or OCI artifact version is deployable. When
`tag` is true, nomad-packs promotes `dev` or `rc` into `main` and creates `<pack>/<version>` on the
resulting main commit. The Action does not know the caller's branch names or release model.

The Action also creates the short-lived GitHub App token and prevents an old branch run from moving
the Pack backwards. The App client ID and private key are required, named inputs; callers source the
private-key value from GitHub Secrets so it remains masked.

It does not build, publish, synchronize, release, or deploy the artifact.
