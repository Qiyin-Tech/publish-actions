# Update Nomad Pack

Update one `nomad-packs` branch after an image or OCI artifact version is deployable. When `tag` is
true, the updater creates the deterministic `<pack>/<version>` tag on the resulting commit.

The Action also creates the short-lived GitHub App token and prevents an old branch run from moving
the Pack backwards. The App client ID and private key are required, named inputs; callers source the
private-key value from GitHub Secrets so it remains masked.

It does not build, publish, synchronize, release, or deploy the artifact.
