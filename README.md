# proton-to-winlator-builder

Automates converting Valve Proton releases into Winlator `.wcp` packages.

## Local usage

```bash
export STEAM_USERNAME=your_user
export STEAM_PASSWORD=your_pass
export PROTON_VERSION=10.0
export WCP_VERSION=10.0-1
./scripts/build_wcp.sh
```

The script downloads Proton via SteamCMD, restructures the `files/` tree into the
Winlator layout, and writes the `.wcp` archive to `./dist`.

## GitHub Actions

The workflow `.github/workflows/build-wcp.yml` can be triggered manually or via
tags like `proton-10.0`. Configure the following repository secrets:

- `STEAM_USERNAME`
- `STEAM_PASSWORD`
- `STEAM_GUARD_CODE` (optional)
