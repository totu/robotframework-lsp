#!/usr/bin/env python3
import sys
import os
import subprocess

def run_command(command, cwd=None, shell=True):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=shell, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        sys.exit(e.returncode)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 release_helper.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    print(f"Building version: {version}")

    # Update version
    print("Updating version...")
    run_command(f"{sys.executable} dev.py set-version {version}")

    # Build wheel
    print("Building wheel...")
    src_dir = os.path.join(base_dir, "src")
    
    # Clean previous builds
    run_command("rm -rf build dist robotframework_lsp.egg-info || true", cwd=src_dir)
    
    # Build
    run_command(f"{sys.executable} setup.py bdist_wheel", cwd=src_dir)
    
    print("\n" + "="*50)
    print(f"Build complete.")
    print(f"Wheel can be found in: {os.path.join(src_dir, 'dist')}")
    print("="*50)

if __name__ == "__main__":
    main()
