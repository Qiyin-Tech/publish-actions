# Update Nomad Pack

Update one `<pack>/<dev|test|rc>` channel after an image or OCI artifact version is deployable. When
`tag` is true, nomad-packs promotes `dev` or `rc` into `main` and creates `<pack>/<version>` on the
resulting main commit. The Action does not know the caller's branch names or release model.

The Action also creates the short-lived GitHub App token and prevents an old branch run from moving
the Pack backwards. The App client ID and private key are required, named inputs; callers source the
private-key value from GitHub Secrets so it remains masked.

It does not build, publish, synchronize, release, or deploy the artifact.

Each dispatch stores a small `deploy-watch-v1-<attempt>-<pack>` artifact with the source run/attempt,
Pack request and exact child run ID returned by GitHub API 2026-03-10. A stale build records
`superseded` without a child. The observer can therefore update one publication card across repositories;
this diagnostic record does not change the selected channel or formal-release semantics.
