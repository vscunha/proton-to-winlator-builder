# proton-to-winlator-builder

Automates converting Valve Proton releases into Winlator `.wcp` packages.

## Local usage

```bash
export STEAM_USERNAME=your_user
export STEAM_PASSWORD=your_pass
./scripts/build_wcp.sh
```

The script downloads Proton via SteamCMD, restructures the `files/` tree into the
Winlator layout, generates `wcp.json`, `profile.json`, and `prefixPack.txz`, and
writes the `.wcp` archive to `./dist`.

If `PROTON_VERSION` is omitted or set to `latest`, the script uses the most
recent Steam build ID as the version. Set `PROTON_VERSION` to a specific release
when needed.

Local runs expect `steamcmd`, `xz`, `zstd`, and `python3` to be available.

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

## Available Proton versions (Steam App IDs)

The workflow input `app_id` should match the Proton release you want to build.
Use the Steam App IDs below when triggering the workflow. These are based on
SteamDB listings as of 2026-02-06, so re-check SteamDB for updates or additional
versions.

| Proton version | Steam App ID | Notes |
| --- | --- | --- |
| Proton Experimental | `1493710` | Rolling experimental builds |
| Proton Hotfix | `2180100` | Emergency hotfix channel |
| Proton 10.0 | `3658110` | Current 10.x beta/stable entry |
| Proton 9.0 | `2805730` | 9.x stable entry |
| Proton 8.0 | `2348590` | 8.x stable entry |
| Proton 7.0 | `1887720` | 7.x stable entry |

Reference links:
- https://steamdb.info/app/1493710/ (Proton Experimental)
- https://steamdb.info/app/2180100/ (Proton Hotfix)
- https://steamdb.info/app/3658110/ (Proton 10.0)
- https://steamdb.info/app/2805730/ (Proton 9.0)
- https://steamdb.info/app/2348590/ (Proton 8.0)
- https://steamdb.info/app/1887720/ (Proton 7.0)
