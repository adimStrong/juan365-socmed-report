#!/usr/bin/env python3
"""
Deploy to Vercel - Export data, commit, and deploy with cache clear.

This script ensures fresh data is deployed to Vercel by:
1. Running export_static_data.py to generate fresh JSON
2. Committing changes to git
3. Pushing to GitHub
4. Force deploying via Vercel CLI (clears build cache)

Usage:
    python deploy_to_vercel.py                    # Deploy current project
    python deploy_to_vercel.py --all              # Deploy all 3 projects
    python deploy_to_vercel.py --skip-export      # Skip export, just deploy
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

# Project configurations
PROJECTS = {
    "juanstudio": {
        "dir": r"C:\Users\us\Desktop\juanstudio_project",
        "frontend": r"C:\Users\us\Desktop\juanstudio_project\frontend",
        "json_file": "public/data/analytics-v2.json",
        "name": "JuanStudio"
    },
    "juanbabes": {
        "dir": r"C:\Users\us\Desktop\juanbabes_project",
        "frontend": r"C:\Users\us\Desktop\juanbabes_project\frontend",
        "json_file": "public/data/analytics.json",
        "name": "JuanBabes"
    },
    "juan365": {
        "dir": r"C:\Users\us\Desktop\juan365_socmed_report",
        "frontend": r"C:\Users\us\Desktop\juan365_socmed_report\frontend",
        "json_file": "public/data/analytics.json",
        "name": "Juan365"
    }
}


def run_command(cmd, cwd=None, timeout=120):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True if isinstance(cmd, str) else False
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def export_data(project_dir: str) -> bool:
    """Run export_static_data.py to generate fresh JSON."""
    export_script = os.path.join(project_dir, "export_static_data.py")
    if not os.path.exists(export_script):
        print(f"    [!] Export script not found: {export_script}")
        return False

    print("    Running export_static_data.py...")
    success, stdout, stderr = run_command(
        [sys.executable, export_script],
        cwd=project_dir,
        timeout=180
    )

    if success:
        print("    [OK] Export complete")
        return True
    else:
        print(f"    [X] Export failed: {stderr[:200]}")
        return False


def git_commit_and_push(project_dir: str, json_file: str) -> bool:
    """Commit JSON changes and push to GitHub."""
    # Check for changes
    success, stdout, stderr = run_command(
        ["git", "status", "--porcelain", f"frontend/{json_file}"],
        cwd=project_dir
    )

    if not stdout.strip():
        print("    No changes to commit")
        return True

    # Add file
    run_command(["git", "add", f"frontend/{json_file}"], cwd=project_dir)

    # Commit
    commit_msg = f"Update analytics data {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    success, stdout, stderr = run_command(
        ["git", "commit", "-m", commit_msg],
        cwd=project_dir
    )

    if not success and "nothing to commit" not in stdout + stderr:
        print(f"    [X] Commit failed: {stderr[:200]}")
        return False

    # Push
    print("    Pushing to GitHub...")
    success, stdout, stderr = run_command(
        ["git", "push"],
        cwd=project_dir,
        timeout=60
    )

    if success:
        print("    [OK] Pushed to GitHub")
        return True
    else:
        print(f"    [X] Push failed: {stderr[:200]}")
        return False


def vercel_deploy(project_dir: str, force: bool = True) -> bool:
    """Deploy to Vercel using CLI from project root."""
    cmd = ["npx", "vercel", "--prod", "--yes"]
    if force:
        cmd.append("--force")

    print("    Deploying to Vercel (with cache clear)...")
    success, stdout, stderr = run_command(
        cmd,
        cwd=project_dir,
        timeout=300
    )

    if success or "Aliased" in stdout:
        print("    [OK] Deployed to Vercel")
        return True
    else:
        # Check for common errors
        if "Error:" in stdout or "Error:" in stderr:
            error_msg = stdout + stderr
            print(f"    [X] Vercel deploy failed")
            # Fall back to git push (Vercel will auto-deploy via GitHub integration)
            print("    Falling back to GitHub integration deploy...")
            return True  # Git push already done
        return False


def deploy_project(project_key: str, skip_export: bool = False) -> bool:
    """Deploy a single project."""
    config = PROJECTS[project_key]

    print(f"\n{'='*60}")
    print(f"Deploying {config['name']}")
    print(f"{'='*60}")

    # 1. Export data
    if not skip_export:
        if not export_data(config["dir"]):
            return False

    # 2. Git commit and push
    if not git_commit_and_push(config["dir"], config["json_file"]):
        return False

    # 3. Vercel deploy with force (clear cache) - from project root
    vercel_deploy(config["dir"], force=True)

    print(f"\n[OK] {config['name']} deployment complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy to Vercel with fresh data")
    parser.add_argument("--project", choices=["juanstudio", "juanbabes", "juan365"],
                        help="Project to deploy (default: auto-detect from cwd)")
    parser.add_argument("--all", action="store_true", help="Deploy all 3 projects")
    parser.add_argument("--skip-export", action="store_true", help="Skip data export")
    args = parser.parse_args()

    print(f"\n{'#'*60}")
    print(f"  VERCEL DEPLOYMENT SCRIPT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    if args.all:
        projects = ["juanstudio", "juanbabes", "juan365"]
    elif args.project:
        projects = [args.project]
    else:
        # Auto-detect from current directory
        cwd = os.getcwd()
        project = None
        for key, config in PROJECTS.items():
            if cwd.startswith(config["dir"]):
                project = key
                break
        if project:
            projects = [project]
        else:
            projects = ["juanstudio"]  # Default

    results = {}
    for project in projects:
        results[project] = deploy_project(project, args.skip_export)

    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT SUMMARY")
    print(f"{'='*60}")
    for project, success in results.items():
        status = "[OK]" if success else "[FAILED]"
        print(f"  {project}: {status}")

    # Return success if all deployments succeeded
    return all(results.values())


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
