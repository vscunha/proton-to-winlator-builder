# Project Context: Proton to Winlator WCP Builder

This project automates the conversion of Valve's Proton compatibility tool into `.wcp` (Winlator Custom Package) format for use on Android devices.

## Core Objectives
1.  **Fetch**: Download specific versions of Proton (e.g., Proton 10.0) using SteamCMD.
2.  **Transform**: Restructure the downloaded files into the standard Wine hierarchy required by Winlator.
3.  **Package**: bundle the files and a generated `wcp.json` manifest into a `.wcp` archive.
4.  **Release**: Automatically publish the `.wcp` file as a GitHub Release asset.

## Tech Stack

- **SteamCMD**: For downloading Proton releases (requires authenticated login)
- **GitHub Actions**: CI/CD pipeline for automation
- **Shell Scripts**: Primary automation language (expected to be added)
- **Packaging**: ZIP-based archives with `.wcp` extension

### Required Secrets
- `STEAM_USERNAME`: Steam account username
- `STEAM_PASSWORD`: Steam account password
- Note: MFA (Steam Guard) is a known blocker; assume Steam Guard is disabled or handled via TOTP secrets

## Coding Guidelines

### File Structure Rules
- **CRITICAL**: When creating `.wcp` archives, do NOT wrap content in a parent folder
- The zip must extract directly to `bin/`, `lib/`, `share/`, and `wcp.json` at the root
- Never add nested parent directories in the archive

### Manifest Format (wcp.json)
Always generate `wcp.json` with this exact structure:
```json
{
  "name": "Proton X.Y",
  "version": "X.Y-Z",
  "description": "Valve's Proton compatibility layer converted for Winlator",
  "wine_version": "proton-X.Y"
}
```

### Path Mapping Rules
When transforming Proton to Wine structure:
- Proton's `files/` directory maps to Wine's `bin/`, `lib/`, and `share/`
- Ensure all necessary libraries and dependencies are included
- Preserve file permissions and symbolic links

### Version Management
- Version in `wcp.json` must match the Proton version being packaged
- Use format: `major.minor-build` (e.g., "10.0-1")

## Project Structure

```
.
├── .github/
│   ├── workflows/       # GitHub Actions workflows
│   └── copilot-instructions.md
├── scripts/             # Build and conversion scripts (if added)
├── README.md
└── LICENSE
```

### Directories to Create (if implementing scripts)
- `scripts/`: Shell scripts for download, transform, and package operations
- `temp/`: Temporary directory for downloads and transformations (should be .gitignored)
- `output/`: Final `.wcp` file output (should be .gitignored)

## Common Pitfalls to Avoid

1.  **Nested Folders**: Don't create a zip with a parent folder containing the structure. The zip must extract directly to `bin/`, `lib/`, `share/`, and `wcp.json`.
2.  **Steam Guard**: CI will fail if the Steam account has Steam Guard enabled without proper handling.
3.  **Missing Files**: Ensure all required Wine components are copied during transformation.
4.  **Incorrect Permissions**: Preserve executable permissions for binaries.
5.  **Path Issues**: Always use absolute paths or properly handle relative paths in scripts.

## Development Workflow

1.  Test locally with a valid Steam account (Steam Guard disabled or TOTP configured).
2.  Verify the generated `.wcp` file structure before uploading to releases.
3.  Always validate the `wcp.json` manifest is correctly generated.
4.  Check that extracted archive has correct structure (no parent folder).

## GitHub Actions Integration

- Workflow should trigger on manual dispatch or on specific tags/releases
- Use repository secrets for `STEAM_USERNAME` and `STEAM_PASSWORD`
- Final `.wcp` file should be uploaded as a release asset
- Include error handling for Steam authentication failures

## Testing Guidelines

When implementing or modifying:
- Test archive extraction to verify structure
- Validate `wcp.json` with JSON linting
- Check that all required Wine directories are present
- Verify file permissions are preserved

## Resources

- README.md: Project overview
- LICENSE: Project licensing information
- GitHub Actions Documentation: https://docs.github.com/en/actions
- SteamCMD Documentation: https://developer.valvesoftware.com/wiki/SteamCMD
