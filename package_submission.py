"""
Automated Submission Packager for Movie Knowledge Graph Project.
Packages the project into a clean, compliant submission.zip archive per instructor guidelines.
Ensures zero secret leakage (excludes .env, data/, logs/, caches).
"""

import os
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SUBMISSION_ZIP = PROJECT_ROOT / "submission.zip"

# Strict exclusion list to prevent credential leaks and bloat
EXCLUDE_DIRS = {
    "data",
    "logs",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".idea",
    ".vscode",
    "venv",
    ".venv"
}

EXCLUDE_FILES = {
    ".env",
    "submission.zip",
    ".DS_Store",
    "Thumbs.db"
}

MANDATORY_INSTRUCTOR_FILES = [
    "docker-compose.yml",
    ".env.example",
    "init/seed.cypher",
    "queries/create_movie.cypher",
    "queries/find_actor_movies.cypher",
    "queries/find_co_actors.cypher",
    "queries/update_movie_rating.cypher",
    "queries/delete_movie.cypher",
    "queries/analytics_degree.cypher",
    "README.md",
]


def create_submission_archive():
    print("\n=======================================================")
    print("  Creating Submission Package: submission.zip")
    print("=======================================================\n")

    # 1. Verify all mandatory files exist
    missing_mandatory = []
    for rel_path in MANDATORY_INSTRUCTOR_FILES:
        target = PROJECT_ROOT / rel_path
        if not target.exists():
            missing_mandatory.append(rel_path)

    if missing_mandatory:
        print(f"[-] ERROR: Missing mandatory submission files: {missing_mandatory}")
        sys.exit(1)

    print("[+] All instructor mandatory files confirmed present.")

    # 2. Build the zip archive
    if SUBMISSION_ZIP.exists():
        SUBMISSION_ZIP.unlink()

    included_count = 0
    with zipfile.ZipFile(SUBMISSION_ZIP, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_ROOT):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in sorted(files):
                if file in EXCLUDE_FILES or file.endswith(".pyc") or file.endswith(".pyo"):
                    continue

                abs_file = Path(root) / file
                rel_path = abs_file.relative_to(PROJECT_ROOT)

                zipf.write(abs_file, arcname=str(rel_path).replace("\\", "/"))
                included_count += 1

    zip_size_kb = SUBMISSION_ZIP.stat().st_size / 1024
    print(f"[+] Successfully bundled {included_count} files into submission.zip ({zip_size_kb:.2f} KB).")

    # 3. Verify archive contents
    print("\n[*] Archive Table of Contents:")
    with zipfile.ZipFile(SUBMISSION_ZIP, "r") as zipf:
        namelist = zipf.namelist()
        for name in sorted(namelist):
            print(f"    - {name}")

        assert ".env" not in namelist, "SECURITY VIOLATION: .env detected in zip archive!"
        for req_f in MANDATORY_INSTRUCTOR_FILES:
            assert req_f in namelist, f"Missing required file in archive: {req_f}"

    print(f"\n[SUCCESS] submission.zip is verified, secure, and ready for instructor evaluation!\n")


if __name__ == "__main__":
    create_submission_archive()
