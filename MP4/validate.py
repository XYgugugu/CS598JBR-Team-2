"""
MP4 Repository Structure Validator
CS598JBR - Fall 2026

Description:
    This script validates the required MP4 repository structure.
    It checks for required directories, configuration files, pipeline code,
    original C projects, generated Rust translations, and execution trajectories.

Installation:
    pip install GitPython colorama

Usage:
    python validate_mp4.py <GitHub Repo URL> [branch]

Example:
    python validate_mp4.py https://github.com/USERNAME/CS598JBR-Team-1.git main

Expected Repository Structure:

CS598JBR-Team-X/
└── MP4/
    ├── README.md
    ├── src/
    │   └── pipeline.py
    ├── configs/
    │   └── config.json
    ├── trajectories/
    │   ├── project_1/
    │   │   └── execution.log
    │   └── project_2/
    │       └── execution.log
    ├── translations/
    │   ├── project_1/
    │   │   ├── Cargo.toml
    │   │   └── src/
    │   │       └── lib.rs
    │   └── project_2/
    │       ├── Cargo.toml
    │       └── src/
    │           └── lib.rs
    └── subjects/
        ├── project_1/
        │   └── original.c
        └── project_2/
            └── original.c

Notes:
    - Filenames shown above are examples; equivalent filenames are allowed.
    - The script checks repository structure, not implementation correctness.
    - It does not run Rust compilation, tests, Clippy, or safety analysis.
    - Passing validation does not guarantee full credit.
"""

import os
import re
import sys
import git
from colorama import Fore, Style


def print_message(level="info", message=""):
    colors = {
        "error": Fore.RED,
        "info": Fore.BLUE,
        "success": Fore.GREEN,
        "warning": Fore.YELLOW,
    }
    print(f"{colors.get(level, Fore.RESET)}{message}{Style.RESET_ALL}")


def validate_repo_format(repo_url):
    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")

    if re.fullmatch(r"CS598JBR-Team-\d+", repo_name):
        print_message("success", f"Valid repository name: {repo_name}")
        return True

    print_message("error", f"Invalid repository name: {repo_name}")
    return False


def clone_repo(repo_url, branch="main"):
    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")

    if os.path.exists(repo_name):
        print_message("info", f"Updating {repo_name}...")
        repo = git.Repo(repo_name)
        repo.git.fetch("origin")
        repo.git.checkout(branch)
        repo.git.pull("origin", branch)
    else:
        print_message("info", f"Cloning {repo_name}...")
        git.Repo.clone_from(repo_url, repo_name, branch=branch)

    return repo_name


def has_files(directory, extension=None):
    """Check for non-empty files, including in subdirectories."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file == ".gitkeep":
                continue
            if extension and not file.endswith(extension):
                continue
            if os.path.getsize(os.path.join(root, file)) > 0:
                return True
    return False


def validate_repo(repo_name):
    mp4_dir = os.path.join(repo_name, "MP4")
    valid = True

    # 1. Check MP4 directory
    if not os.path.isdir(mp4_dir):
        print_message("error", "Missing MP4/ directory!")
        return False

    # 2. Check README
    readme = os.path.join(mp4_dir, "README.md")
    if os.path.isfile(readme) and os.path.getsize(readme) > 0:
        print_message("success", "MP4/README.md found!")
    else:
        print_message("error", "Missing or empty MP4/README.md")
        valid = False

    # 3. Check required directories
    required_dirs = [
        "src",
        "configs",
        "subjects/project_1",
        "subjects/project_2",
        "translations/project_1",
        "translations/project_2",
        "trajectories/project_1",
        "trajectories/project_2",
    ]

    for directory in required_dirs:
        path = os.path.join(mp4_dir, directory)

        if os.path.isdir(path):
            print_message("success", f"{directory}/ found!")
        else:
            print_message("error", f"Missing directory: {directory}/")
            valid = False

    # 4. Check pipeline code and configurations
    for directory in ["src", "configs"]:
        path = os.path.join(mp4_dir, directory)

        if not has_files(path):
            print_message("error", f"{directory}/ contains no non-empty files!")
            valid = False
        else:
            print_message("success", f"{directory}/ contains files!")

    # 5. Check both assigned projects
    for i in [1, 2]:
        print_message("info", f"\nChecking Project {i}...")

        subject = os.path.join(mp4_dir, "subjects", f"project_{i}")
        translation = os.path.join(mp4_dir, "translations", f"project_{i}")
        trajectory = os.path.join(mp4_dir, "trajectories", f"project_{i}")

        # Original C source
        if has_files(subject, ".c"):
            print_message("success", f"Project {i}: C source files found!")
        else:
            print_message("error", f"Project {i}: No C source files found!")
            valid = False

        # Generated Rust source
        if has_files(translation, ".rs"):
            print_message("success", f"Project {i}: Rust source files found!")
        else:
            print_message("error", f"Project {i}: No Rust source files found!")
            valid = False

        # Cargo.toml (recommended for standalone builds)
        cargo_file = os.path.join(translation, "Cargo.toml")
        if os.path.isfile(cargo_file):
            print_message("success", f"Project {i}: Cargo.toml found!")
        else:
            print_message(
                "warning",
                f"Project {i}: Cargo.toml not found in translation directory."
            )

        # Agent execution logs
        if has_files(trajectory):
            print_message("success", f"Project {i}: Trajectory files found!")
        else:
            print_message("error", f"Project {i}: Trajectory files missing or empty!")
            valid = False

    return valid


def grade_repo(repo_url, branch="main"):
    if not validate_repo_format(repo_url):
        return False

    try:
        repo_name = clone_repo(repo_url, branch)
        result = validate_repo(repo_name)

        print("\n" + "=" * 50)

        if result:
            print_message("success", "MP4 STRUCTURE VALIDATION PASSED!")
        else:
            print_message("error", "MP4 STRUCTURE VALIDATION FAILED!")

        print_message(
            "info",
            "Note: Passing validation does not guarantee full credit."
        )
        return result

    except Exception as e:
        print_message("error", f"Validation error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) not in [2, 3]:
        print("Usage: python validate_mp4.py <GitHub Repo URL> [branch]")
        sys.exit(1)

    repo_url = sys.argv[1]
    branch = sys.argv[2] if len(sys.argv) == 3 else "main"

    sys.exit(0 if grade_repo(repo_url, branch) else 1)
