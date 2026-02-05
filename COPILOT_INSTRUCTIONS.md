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
  "name": "Proton 10.0",
  "version": "10.0-1",
  "description": "Valve's Proton compatibility layer converted for Winlator",
  "wine_version": "proton-10.0"
}
```

## Key Implementation Details
*   **File Restructuring**: Proton's directory structure differs from Wine's. The conversion must map Proton paths to expected Wine paths (e.g., `files/` → `bin/`, `lib/`, `share/`).
*   **Dependency Handling**: Ensure all necessary libraries and dependencies are included in the package.
*   **Versioning**: The version in `wcp.json` should match the Proton version being packaged.

## Common Pitfalls to Avoid
1.  **Nested Folders**: Don't create a zip with a parent folder containing the structure. The zip must extract directly to `bin/`, `lib/`, `share/`, and `wcp.json`.
2.  **Steam Guard**: CI will fail if the Steam account has Steam Guard enabled without proper handling.
3.  **Missing Files**: Ensure all required Wine components are copied during transformation.

## Development Workflow
1.  Test locally with a valid Steam account (Steam Guard disabled or TOTP configured).
2.  Verify the generated `.wcp` file structure before uploading to releases.
3.  Always validate the `wcp.json` manifest is correctly generated.

## GitHub Actions Integration
*   The workflow should trigger on manual dispatch or on specific tags/releases.
*   Use repository secrets for `STEAM_USERNAME` and `STEAM_PASSWORD`.
*   The final `.wcp` file should be uploaded as a release asset.
