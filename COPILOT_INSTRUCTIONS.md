# Project Context: Proton to Winlator WCP Builder

This project automates the conversion of Valve's Proton compatibility tool into `.wcp` (Winlator Custom Package) format for use on Android devices.

## Core Objectives
1.  **Fetch**: Download specific versions of Proton (e.g., Proton 10.0) using SteamCMD.
2.  **Transform**: Restructure the downloaded files into the standard Wine hierarchy required by Winlator.
3.  **Package**: bundle the files and a generated `wcp.json` manifest into a `.wcp` archive.
4.  **Release**: Automatically publish the `.wcp` file as a GitHub Release asset.

## Technical Constraints & Requirements
*   **SteamCMD**: Must be used for downloading. Anonymous login does NOT work for Proton; authenticated login is required.
*   **CI/CD**: The pipeline uses GitHub Actions.
*   **Secrets**: `STEAM_USERNAME` and `STEAM_PASSWORD` are required secrets. MFA (Steam Guard) is a known blocker for CI; the pipeline must attempt to handle this or assume Steam Guard is disabled/handled via TOTP secrets if implemented.
*   **Output Format**: 
    *   Extension: `.wcp` (which is just a renamed `.zip`).
    *   Structure: Root must contain `bin/`, `lib/`, `share/`, and `wcp.json`.
    *   **CRITICAL**: Do not wrap the content inside a parent folder in the zip. `wcp.json` must be at the root of the archive.

## Manifest Structure (wcp.json)
```json
{
  "name": "Proton <version>",
  "version": "<version>",
  "description": "Proton compatibility layer for Winlator",
  "author": "Valve Software (repackaged)",
  "wine_version": "<corresponding_wine_version>"
}
```

## Development Workflow
1.  **Script Development**: All conversion logic should be implemented in shell scripts or Python.
2.  **Testing**: Test locally before pushing to CI.
3.  **Secrets Management**: Never commit Steam credentials. Use GitHub Secrets.
4.  **Versioning**: The Proton version should be configurable (e.g., via workflow input or environment variable).

## File Structure Expectations
After transformation, the directory structure should look like:
```
output/
├── bin/          # Executables (wine, wineserver, etc.)
├── lib/          # Libraries (wine libraries, .so files)
├── share/        # Shared resources (wine data files)
└── wcp.json      # Manifest file
```

## Known Issues & Workarounds
*   **Steam Guard**: CI cannot interactively handle Steam Guard. Use an account with it disabled or implement TOTP-based automation.
*   **Download Failures**: SteamCMD can be flaky. Implement retry logic.
*   **Large Files**: Proton downloads can be 1GB+. Ensure adequate storage and timeout settings in CI.

## References
*   Valve Proton: https://github.com/ValveSoftware/Proton
*   SteamCMD Documentation: https://developer.valvesoftware.com/wiki/SteamCMD
*   Winlator: https://github.com/brunodev85/winlator
