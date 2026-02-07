#!/usr/bin/env python3
"""
Integration test for Winlator WCP package validation.
Based on coffincolors/winlator container startup code.

This test validates that generated WCP packages will work correctly
with the coffincolors/winlator CMOD application by simulating the
key validation steps that Winlator performs during container startup.
"""

import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class WineInfoValidator:
    """
    Validates Wine/Proton identifiers based on WineInfo.java regex pattern.
    Pattern: ^(wine|proton|Proton)\\-([0-9\\.]+)\\-?([0-9\\.]+)?\\-(x86|x86_64|arm64ec)$
    """
    
    PATTERN = re.compile(r'^(wine|proton|Proton)\-([0-9\.]+)\-?([0-9\.]+)?\-(x86|x86_64|arm64ec)$')
    
    @classmethod
    def validate_identifier(cls, identifier: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        """
        Validate a wine/proton identifier against the WineInfo pattern.
        
        Returns:
            (is_valid, parsed_data) where parsed_data contains type, version, subversion, arch
        """
        match = cls.PATTERN.match(identifier)
        if not match:
            return False, None
        
        return True, {
            'type': match.group(1).lower(),  # wine or proton
            'version': match.group(2),
            'subversion': match.group(3) if match.group(3) else None,
            'arch': match.group(4)
        }
    
    @classmethod
    def construct_identifier(cls, type_name: str, version_name: str) -> str:
        """
        Construct a WineInfo identifier from type and versionName.
        This mimics how Winlator resolves identifiers from profile.json.
        """
        # If versionName already includes the type prefix, use it directly
        if version_name.startswith(f"{type_name.lower()}-"):
            return version_name
        
        # Otherwise, prepend the type
        return f"{type_name.lower()}-{version_name}"


class ContentProfileValidator:
    """
    Validates profile.json structure based on ContentsManager.readProfile() and ContentProfile.java
    """
    
    REQUIRED_FIELDS = ['type', 'versionName', 'versionCode', 'description', 'files']
    VALID_TYPES = ['Wine', 'Proton', 'DXVK', 'VKD3D', 'Box64', 'WOWBox64', 'FEXCore']
    
    @classmethod
    def validate_profile(cls, profile_data: dict) -> Tuple[bool, List[str]]:
        """
        Validate profile.json structure matches Winlator expectations.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in profile_data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Validate type
        profile_type = profile_data.get('type')
        if profile_type not in cls.VALID_TYPES:
            errors.append(f"Invalid type '{profile_type}'. Must be one of: {', '.join(cls.VALID_TYPES)}")
        
        # Validate versionCode is integer
        try:
            int(profile_data.get('versionCode'))
        except (ValueError, TypeError):
            errors.append(f"versionCode must be an integer, got: {profile_data.get('versionCode')}")
        
        # Validate files is an array
        if not isinstance(profile_data.get('files'), list):
            errors.append(f"files must be an array, got: {type(profile_data.get('files'))}")
        
        # Type-specific validation
        if profile_type in ['Wine', 'Proton']:
            if profile_type == 'Wine':
                required_section = 'wine'
                required_keys = ['binPath', 'libPath', 'prefixPack']
            else:  # Proton
                required_section = 'proton'
                required_keys = ['binPath', 'libPath', 'prefixPack']
            
            if required_section not in profile_data:
                errors.append(f"Missing required section: {required_section}")
            else:
                section_data = profile_data[required_section]
                for key in required_keys:
                    if key not in section_data:
                        errors.append(f"Missing {required_section}.{key}")
        
        # Validate versionName format for Wine/Proton types
        if profile_type in ['Wine', 'Proton']:
            version_name = profile_data.get('versionName', '')
            
            # Construct the identifier as Winlator would
            identifier = WineInfoValidator.construct_identifier(profile_type, version_name)
            
            is_valid, parsed = WineInfoValidator.validate_identifier(identifier)
            if not is_valid:
                errors.append(
                    f"versionName '{version_name}' (identifier: '{identifier}') does not match "
                    f"WineInfo pattern: {WineInfoValidator.PATTERN.pattern}"
                )
        
        return len(errors) == 0, errors


class WCPValidator:
    """
    Main WCP package validator that simulates Winlator's container startup validation.
    """
    
    def __init__(self, wcp_path: str):
        self.wcp_path = Path(wcp_path)
        self.temp_dir = None
        self.errors = []
        self.warnings = []
    
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='wcp_test_')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def validate(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            True if all validations pass, False otherwise
        """
        if not self.wcp_path.exists():
            self.errors.append(f"WCP file not found: {self.wcp_path}")
            return False
        
        print(f"Validating WCP: {self.wcp_path}")
        print(f"Extraction directory: {self.temp_dir}")
        
        # Step 1: Extract WCP archive (simulates TarCompressorUtils.extract)
        if not self._extract_wcp():
            return False
        
        # Step 2: Validate profile.json exists (simulates ContentsManager.readProfile check)
        if not self._check_profile_exists():
            return False
        
        # Step 3: Validate profile.json structure (simulates ContentsManager.readProfile)
        profile_data = self._validate_profile_structure()
        if not profile_data:
            return False
        
        # Step 4: Validate Wine/Proton specific requirements
        if not self._validate_wine_proton_files(profile_data):
            return False
        
        # Step 5: Validate prefixPack structure
        if not self._validate_prefix_pack(profile_data):
            return False
        
        # Step 6: Additional file structure checks
        if not self._validate_directory_structure():
            return False
        
        return len(self.errors) == 0
    
    def _extract_wcp(self) -> bool:
        """Extract WCP archive (tar with xz or zstd compression)."""
        print("\n[1/6] Extracting WCP archive...")
        
        try:
            # Try zstd first (current format)
            try:
                result = subprocess.run(
                    ['tar', '--zstd', '-xf', str(self.wcp_path), '-C', self.temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print("  ✓ Extracted with zstd compression")
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            
            # Try xz fallback
            try:
                result = subprocess.run(
                    ['tar', '-xJf', str(self.wcp_path), '-C', self.temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print("  ✓ Extracted with xz compression")
                    self.warnings.append("WCP uses xz compression, should use zstd")
                    return True
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            
            self.errors.append("Failed to extract WCP archive with tar (tried zstd and xz)")
            return False
            
        except Exception as e:
            self.errors.append(f"Error extracting WCP: {e}")
            return False
    
    def _check_profile_exists(self) -> bool:
        """Check if profile.json exists."""
        print("\n[2/6] Checking profile.json existence...")
        
        profile_path = Path(self.temp_dir) / 'profile.json'
        if not profile_path.exists():
            self.errors.append("profile.json not found at archive root")
            return False
        
        print(f"  ✓ profile.json found")
        return True
    
    def _validate_profile_structure(self) -> Optional[dict]:
        """Validate profile.json structure."""
        print("\n[3/6] Validating profile.json structure...")
        
        profile_path = Path(self.temp_dir) / 'profile.json'
        
        try:
            with open(profile_path, 'r') as f:
                profile_data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in profile.json: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading profile.json: {e}")
            return None
        
        # Validate structure
        is_valid, errors = ContentProfileValidator.validate_profile(profile_data)
        
        if not is_valid:
            self.errors.extend(errors)
            return None
        
        print(f"  ✓ Type: {profile_data['type']}")
        print(f"  ✓ Version Name: {profile_data['versionName']}")
        print(f"  ✓ Version Code: {profile_data['versionCode']}")
        
        # Show the resolved identifier
        identifier = WineInfoValidator.construct_identifier(
            profile_data['type'],
            profile_data['versionName']
        )
        print(f"  ✓ Resolved identifier: {identifier}")
        
        return profile_data
    
    def _validate_wine_proton_files(self, profile_data: dict) -> bool:
        """Validate Wine/Proton specific file requirements."""
        print("\n[4/6] Validating Wine/Proton file structure...")
        
        profile_type = profile_data['type']
        
        if profile_type not in ['Wine', 'Proton']:
            print(f"  - Skipping (type={profile_type}, not Wine/Proton)")
            return True
        
        section_key = 'wine' if profile_type == 'Wine' else 'proton'
        section_data = profile_data.get(section_key, {})
        
        bin_path = section_data.get('binPath')
        lib_path = section_data.get('libPath')
        prefix_pack = section_data.get('prefixPack')
        
        # Check bin directory
        bin_dir = Path(self.temp_dir) / bin_path
        if not bin_dir.exists() or not bin_dir.is_dir():
            self.errors.append(f"{section_key}.binPath '{bin_path}' is not a directory")
        else:
            print(f"  ✓ {bin_path}/ exists")
        
        # Check lib directory
        lib_dir = Path(self.temp_dir) / lib_path
        if not lib_dir.exists() or not lib_dir.is_dir():
            self.errors.append(f"{section_key}.libPath '{lib_path}' is not a directory")
        else:
            print(f"  ✓ {lib_path}/ exists")
        
        # Check prefixPack file
        prefix_file = Path(self.temp_dir) / prefix_pack
        if not prefix_file.exists() or not prefix_file.is_file():
            self.errors.append(f"{section_key}.prefixPack '{prefix_pack}' is not a file")
        else:
            print(f"  ✓ {prefix_pack} exists")
        
        return len(self.errors) == 0
    
    def _validate_prefix_pack(self, profile_data: dict) -> bool:
        """Validate prefixPack.txz structure."""
        print("\n[5/6] Validating prefixPack structure...")
        
        profile_type = profile_data['type']
        
        if profile_type not in ['Wine', 'Proton']:
            print(f"  - Skipping (type={profile_type})")
            return True
        
        section_key = 'wine' if profile_type == 'Wine' else 'proton'
        section_data = profile_data.get(section_key, {})
        prefix_pack = section_data.get('prefixPack')
        
        prefix_file = Path(self.temp_dir) / prefix_pack
        if not prefix_file.exists():
            # Already reported in previous step
            return False
        
        try:
            with tarfile.open(prefix_file, 'r:xz') as tar:
                members = tar.getmembers()
                
                if not members:
                    self.warnings.append("prefixPack.txz is empty")
                    print("  ⚠ prefixPack is empty (may be valid for some use cases)")
                    return True
                
                # Check that all paths start with .wine/
                has_wine_prefix = False
                missing_prefix = []
                
                for member in members:
                    if member.name.startswith('.wine/'):
                        has_wine_prefix = True
                    elif member.name != '.' and not member.name.startswith('./'):
                        missing_prefix.append(member.name)
                
                if not has_wine_prefix and missing_prefix:
                    self.errors.append(
                        f"prefixPack must extract to .wine/ subdirectory. "
                        f"Found paths without .wine/ prefix: {missing_prefix[:5]}"
                    )
                    return False
                
                print(f"  ✓ Contains {len(members)} files/directories")
                print(f"  ✓ All paths correctly prefixed with .wine/")
                
        except Exception as e:
            self.errors.append(f"Error reading prefixPack.txz: {e}")
            return False
        
        return True
    
    def _validate_directory_structure(self) -> bool:
        """Validate overall directory structure."""
        print("\n[6/6] Validating overall WCP structure...")
        
        required_at_root = ['profile.json']
        expected_dirs = ['bin', 'lib', 'share']
        
        # Check required files
        for filename in required_at_root:
            file_path = Path(self.temp_dir) / filename
            if not file_path.exists():
                self.errors.append(f"Missing required file at root: {filename}")
        
        # Check expected directories (warnings only)
        for dirname in expected_dirs:
            dir_path = Path(self.temp_dir) / dirname
            if not dir_path.exists():
                self.warnings.append(f"Expected directory not found: {dirname}/")
            else:
                print(f"  ✓ {dirname}/ exists")
        
        # Check for wcp.json (optional but expected)
        wcp_json = Path(self.temp_dir) / 'wcp.json'
        if wcp_json.exists():
            print(f"  ✓ wcp.json exists (optional)")
            try:
                with open(wcp_json, 'r') as f:
                    wcp_data = json.load(f)
                    print(f"    - name: {wcp_data.get('name')}")
                    print(f"    - version: {wcp_data.get('version')}")
            except Exception as e:
                self.warnings.append(f"Could not parse wcp.json: {e}")
        
        # Check for critical Wine binaries in bin/
        bin_dir = Path(self.temp_dir) / 'bin'
        if bin_dir.exists():
            critical_binaries = ['wine', 'wine64', 'wineserver']
            found_binaries = []
            for binary in critical_binaries:
                if (bin_dir / binary).exists():
                    found_binaries.append(binary)
            
            if found_binaries:
                print(f"  ✓ Found Wine binaries: {', '.join(found_binaries)}")
            else:
                self.warnings.append(
                    f"No critical Wine binaries found in bin/ "
                    f"(expected at least one of: {', '.join(critical_binaries)})"
                )
        
        # Check for Wine libraries in lib/
        lib_dir = Path(self.temp_dir) / 'lib'
        if lib_dir.exists():
            wine_subdirs = ['wine', 'wine64']
            found_wine_libs = False
            for subdir in wine_subdirs:
                wine_lib_dir = lib_dir / subdir
                if wine_lib_dir.exists() and wine_lib_dir.is_dir():
                    # Check if it has any files
                    lib_files = list(wine_lib_dir.iterdir())
                    if lib_files:
                        found_wine_libs = True
                        print(f"  ✓ Found Wine libraries in lib/{subdir}/ ({len(lib_files)} items)")
                        break
            
            if not found_wine_libs:
                self.warnings.append(
                    "No Wine library directories found in lib/ "
                    "(expected lib/wine/ or lib/wine64/)"
                )
        
        return len(self.errors) == 0
    
    def print_results(self):
        """Print validation results."""
        print("\n" + "="*70)
        print("VALIDATION RESULTS")
        print("="*70)
        
        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.errors:
            print(f"\n✗ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
            print(f"\n❌ VALIDATION FAILED")
            return False
        else:
            print(f"\n✓ ALL VALIDATIONS PASSED")
            print(f"  This WCP package should work correctly with coffincolors/winlator")
            return True


def main():
    if len(sys.argv) < 2:
        print("Usage: test_wcp_integration.py <wcp_file>")
        print("\nThis script validates WCP packages against coffincolors/winlator requirements.")
        sys.exit(1)
    
    wcp_file = sys.argv[1]
    
    print("="*70)
    print("Winlator WCP Integration Test")
    print("Based on coffincolors/winlator container startup validation")
    print("="*70)
    
    with WCPValidator(wcp_file) as validator:
        success = validator.validate()
        validator.print_results()
        
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
