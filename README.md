# proton-to-winlator-builder

Automates converting Valve Proton releases into Winlator `.wcp` packages.

## Local usage

```bash
export STEAM_USERNAME=your_user
export STEAM_PASSWORD=your_pass
export PROTON_VERSION=latest
./scripts/build_wcp.sh
```

The script downloads Proton via SteamCMD, restructures the `files/` tree into the
Winlator layout, and writes the `.wcp` archive to `./dist`.

If `PROTON_VERSION` is omitted or set to `latest`, the script uses the most
recent Steam build ID as the version.

Local runs expect `steamcmd`, `zip`, and `python3` to be available.

## GitHub Actions

The workflow `.github/workflows/build-wcp.yml` can be triggered manually (defaults
to the latest Proton build) or via tags like `proton-10.0`. Configure the
following repository secrets:

- `STEAM_USERNAME`
- `STEAM_PASSWORD`
- `STEAM_GUARD_CODE` (optional)

The workflow installs `steamcmd` from the Ubuntu repositories and logs the
package version via `apt-cache policy` so you can pin the runner image if a
specific version is required.
