#!/usr/bin/env python3
"""
AEGIS to Git Repository Import Script

This script imports an AEGIS source code repository into a Git repository,
preserving the original branch structure and commit comments.

AEGIS (Automated Electronic Generation of Information Systems) is a legacy
configuration management system that predates modern version control systems.
This tool helps migrate AEGIS repositories to Git for modern workflows.
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class AegisChange:
    """Represents an AEGIS change (commit)."""
    
    def __init__(self, number: int, branch_name: str):
        self.number = number
        self.branch_name = branch_name
        self.brief_description = ""
        self.description = ""
        self.author = "aegis-user"
        self.timestamp = None
        self.delta_number = 0
        self.state = ""
        self.files = []  # List of (filename, action)
        
    def __repr__(self):
        return f"Change({self.number}, delta={self.delta_number}, {self.brief_description[:30]})"


class AegisRepository:
    """Class to handle AEGIS repository operations."""
    
    def __init__(self, aegis_path: str):
        """
        Initialize AEGIS repository handler.
        
        Args:
            aegis_path: Path to the AEGIS repository
        """
        self.aegis_path = Path(aegis_path).resolve()
        self.project_name = None
        self.branches = {}  # branch_name -> list of AegisChange objects
        
        # Verify AEGIS repository exists
        if not self.aegis_path.exists():
            raise ValueError(f"AEGIS repository path does not exist: {aegis_path}")
    
    def parse_repository(self) -> bool:
        """
        Parse the AEGIS repository to extract project information,
        changes, branches, and commit history.
        
        Returns:
            True if parsing was successful, False otherwise
        """
        print(f"Parsing AEGIS repository at: {self.aegis_path}")
        
        # Use directory name as project name
        self.project_name = self.aegis_path.name
        print(f"Project name: {self.project_name}")
        
        # Look for info/change directory structure
        info_path = self.aegis_path / "info" / "change" / "0"
        if not info_path.exists():
            print("Error: info/change/0 directory not found. This doesn't appear to be a valid AEGIS repository.")
            return False
        
        # Scan for branches
        self._scan_for_branches(info_path)
        
        if not self.branches:
            print("Warning: No branches found in AEGIS repository")
            return False
        
        print(f"\nFound {len(self.branches)} branch(es):")
        for branch_name in sorted(self.branches.keys()):
            changes = self.branches[branch_name]
            print(f"  Branch '{branch_name}': {len(changes)} change(s)")
        
        return True
    
    def _scan_for_branches(self, info_path: Path):
        """
        Scan info/change/0 directory for branches.
        
        Args:
            info_path: Path to info/change/0 directory
        """
        # Look for *.branch directories
        for entry in info_path.iterdir():
            if entry.is_dir() and entry.name.endswith('.branch'):
                branch_num = entry.name.replace('.branch', '')
                branch_subdir = entry / "0"
                if branch_subdir.exists() and branch_subdir.is_dir():
                    self._parse_branch(branch_num, branch_subdir)
    
    def _parse_branch(self, branch_num: str, branch_path: Path):
        """
        Parse a single branch directory.
        
        Args:
            branch_num: Branch number (e.g., "001")
            branch_path: Path to branch directory (e.g., info/change/0/001.branch/0)
        """
        branch_name = f"branch-{branch_num}"
        print(f"\nParsing branch {branch_num}...")
        
        changes = []
        
        # Find all numbered change files (without extension)
        for entry in sorted(branch_path.iterdir()):
            if entry.is_file() and re.match(r'^\d+$', entry.name):
                change_num = int(entry.name)
                fs_file = branch_path / f"{entry.name}.fs"
                
                if fs_file.exists():
                    change = self._parse_change(entry, fs_file, branch_num)
                    if change:
                        changes.append(change)
                        print(f"  Parsed change #{change_num}: {change.brief_description}")
        
        # Sort by delta number or timestamp
        changes.sort(key=lambda c: (c.delta_number if c.delta_number else 999999, c.timestamp if c.timestamp else 0))
        
        self.branches[branch_name] = changes
    
    def _parse_change(self, meta_file: Path, fs_file: Path, branch_num: str) -> Optional[AegisChange]:
        """
        Parse a single change from metadata and file state files.
        
        Args:
            meta_file: Path to change metadata file (e.g., "010")
            fs_file: Path to file state file (e.g., "010.fs")
            branch_num: Branch number
            
        Returns:
            AegisChange object or None if parsing failed
        """
        change_num = int(meta_file.name)
        branch_name = f"branch-{branch_num}"
        change = AegisChange(change_num, branch_name)
        
        try:
            # Parse metadata file
            with open(meta_file, 'r', encoding='utf-8', errors='ignore') as f:
                meta_content = f.read()
            
            # Extract brief description (handle escaped quotes)
            match = re.search(r'brief_description\s*=\s*"((?:[^"\\]|\\.)+)"', meta_content)
            if match:
                # Unescape the string
                change.brief_description = match.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            
            # Extract description (handle escaped quotes)
            match = re.search(r'(?<!brief_)description\s*=\s*"((?:[^"\\]|\\.)+)"', meta_content)
            if match:
                change.description = match.group(1).replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            if not change.description or change.description == change.brief_description:
                change.description = change.brief_description
            
            # Extract delta number
            match = re.search(r'delta_number\s*=\s*(\d+)', meta_content)
            if match:
                change.delta_number = int(match.group(1))
            
            # Extract state
            match = re.search(r'state\s*=\s*(\w+)', meta_content)
            if match:
                change.state = match.group(1)
            
            # Extract timestamp and author from history
            # Look for integrate_pass or develop_end actions
            history_matches = re.findall(
                r'when\s*=\s*(\d+);[^}]*what\s*=\s*(\w+);[^}]*who\s*=\s*"?(\w+)"?',
                meta_content
            )
            
            for timestamp_str, action, who in history_matches:
                timestamp = int(timestamp_str)
                if action in ['integrate_pass', 'develop_end_2ai', 'develop_end']:
                    change.timestamp = timestamp
                    change.author = who
            
            # If no timestamp found, use first entry
            if not change.timestamp and history_matches:
                change.timestamp = int(history_matches[0][0])
                change.author = history_matches[0][2]
            
            # Parse file state file
            with open(fs_file, 'r', encoding='utf-8', errors='ignore') as f:
                fs_content = f.read()
            
            # Extract files and actions
            file_matches = re.findall(
                r'file_name\s*=\s*"([^"]+)";\s*action\s*=\s*(\w+)',
                fs_content
            )
            
            for filename, action in file_matches:
                change.files.append((filename, action))
            
            return change
            
        except Exception as e:
            print(f"Warning: Could not parse change {change_num}: {e}")
            return None
    
    def get_branch_baseline_path(self, branch_name: str) -> Optional[Path]:
        """
        Get the path to the baseline directory for a branch.
        
        Args:
            branch_name: Branch name (e.g., "branch-001")
            
        Returns:
            Path to baseline directory or None if not found
        """
        # Extract branch number from name
        match = re.search(r'branch-(\d+)', branch_name)
        if not match:
            return None
        
        branch_num = match.group(1)
        
        # Try different possible locations
        possible_paths = [
            self.aegis_path / f"branch.{int(branch_num)}" / "baseline",
            self.aegis_path / f"branch.{branch_num}" / "baseline",
            self.aegis_path / "baseline",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
        
        return None


class GitImporter:
    """Class to handle Git import operations."""
    
    def __init__(self, git_path: str, force: bool = False, verbose: bool = False):
        """
        Initialize Git importer.
        
        Args:
            git_path: Path to the Git repository
            force: Force overwrite if repository exists
            verbose: Enable verbose output
        """
        self.git_path = Path(git_path).resolve()
        self.force = force
        self.verbose = verbose
    
    def initialize_repository(self) -> bool:
        """
        Initialize a new Git repository.
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\nInitializing Git repository at: {self.git_path}")
        
        # Check if directory exists
        if self.git_path.exists():
            if not self.force:
                print(f"Error: Directory already exists: {self.git_path}")
                print("Use --force to overwrite")
                return False
            else:
                print(f"Removing existing directory: {self.git_path}")
                shutil.rmtree(self.git_path)
        
        # Create directory
        self.git_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize git repository
        try:
            subprocess.run(
                ['git', 'init'],
                cwd=self.git_path,
                check=True,
                capture_output=True
            )
            print("Git repository initialized successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error initializing Git repository: {e}")
            return False
    
    def import_changes(self, aegis_repo: AegisRepository) -> bool:
        """
        Import AEGIS changes into Git repository.
        
        Args:
            aegis_repo: AegisRepository object with parsed changes
            
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("Starting import of AEGIS changes to Git")
        print("=" * 60)
        
        # Import each branch
        for branch_name in sorted(aegis_repo.branches.keys()):
            changes = aegis_repo.branches[branch_name]
            if not changes:
                print(f"\nSkipping empty branch: {branch_name}")
                continue
            
            self._import_branch(branch_name, changes, aegis_repo)
        
        print("\n" + "=" * 60)
        print("Import completed successfully!")
        print("=" * 60)
        
        return True
    
    def _import_branch(self, branch_name: str, changes: List[AegisChange], aegis_repo: AegisRepository):
        """
        Import a single branch.
        
        Args:
            branch_name: Name of the branch
            changes: List of AegisChange objects
            aegis_repo: AegisRepository object
        """
        print(f"\nImporting branch: {branch_name} ({len(changes)} changes)")
        
        # Create branch if not first
        if branch_name != sorted(aegis_repo.branches.keys())[0]:
            self._run_git(['checkout', '-b', branch_name])
        
        # Get baseline path for this branch
        baseline_path = aegis_repo.get_branch_baseline_path(branch_name)
        if not baseline_path:
            print(f"Warning: Could not find baseline directory for {branch_name}")
            return
        
        print(f"Using baseline: {baseline_path}")
        
        # Import each change
        for i, change in enumerate(changes, 1):
            self._import_change(change, baseline_path, i, len(changes))
    
    def _import_change(self, change: AegisChange, baseline_path: Path, index: int, total: int):
        """
        Import a single change as a Git commit.
        
        Args:
            change: AegisChange object
            baseline_path: Path to baseline directory
            index: Current change index
            total: Total number of changes
        """
        print(f"  [{index}/{total}] Change #{change.number}: {change.brief_description}")
        
        # Copy files from baseline
        # For the first commit, copy all files
        # For subsequent commits, we need to apply the changes incrementally
        # For simplicity, we'll copy all files for now (this preserves the final state)
        
        # Only copy on first commit or if files changed
        if index == 1 or change.files:
            self._copy_baseline_files(baseline_path)
        
        # Stage changes
        self._run_git(['add', '-A'])
        
        # Create commit
        commit_msg = f"{change.brief_description}\n\n{change.description}"
        if change.delta_number:
            commit_msg += f"\n\nDelta: {change.delta_number}"
        commit_msg += f"\nAEGIS Change: {change.number}"
        
        # Set author and date
        env = os.environ.copy()
        author_email = f"{change.author}@aegis"
        env['GIT_AUTHOR_NAME'] = change.author
        env['GIT_AUTHOR_EMAIL'] = author_email
        env['GIT_COMMITTER_NAME'] = change.author
        env['GIT_COMMITTER_EMAIL'] = author_email
        
        if change.timestamp:
            date_str = datetime.fromtimestamp(change.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            env['GIT_AUTHOR_DATE'] = date_str
            env['GIT_COMMITTER_DATE'] = date_str
        
        try:
            self._run_git(['commit', '-m', commit_msg, '--allow-empty'], env=env)
            print(f"    ✓ Committed change #{change.number}")
        except subprocess.CalledProcessError:
            # Commit might fail if no changes, that's ok
            print(f"    ⚠ No changes to commit for #{change.number}")
    
    def _copy_baseline_files(self, baseline_path: Path):
        """
        Copy files from AEGIS baseline to Git repository.
        
        Args:
            baseline_path: Path to AEGIS baseline directory
        """
        # Copy all files except ,D files (delta markers)
        for item in baseline_path.rglob('*'):
            if item.is_file() and not item.name.endswith(',D'):
                rel_path = item.relative_to(baseline_path)
                dest_path = self.git_path / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Remove existing file if it's read-only
                if dest_path.exists():
                    dest_path.chmod(0o644)
                    dest_path.unlink()
                
                shutil.copy2(item, dest_path)
                # Make sure the destination is writable
                dest_path.chmod(0o644)
    
    def _run_git(self, args: List[str], env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """
        Run a git command.
        
        Args:
            args: Git command arguments
            env: Optional environment variables
            
        Returns:
            CompletedProcess object
        """
        if env is None:
            env = os.environ.copy()
        
        if self.verbose:
            print(f"    Running: git {' '.join(args)}")
        
        return subprocess.run(
            ['git'] + args,
            cwd=self.git_path,
            check=True,
            capture_output=not self.verbose,
            env=env
        )


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Import AEGIS repository into Git',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i /path/to/aegis/repo -o /path/to/git/repo
  %(prog)s -i ./aegis-project -o ./git-project --force --verbose
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Path to AEGIS repository'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Path to output Git repository'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force overwrite if output directory exists'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 60)
    print("AEGIS to Git Repository Import Tool")
    print("=" * 60)
    print(f"Input AEGIS repository: {args.input}")
    print(f"Output Git repository:  {args.output}")
    print("=" * 60)
    
    try:
        # Step 1: Parse AEGIS repository
        print("\n[Step 1/3] Parsing AEGIS repository...")
        aegis_repo = AegisRepository(args.input)
        if not aegis_repo.parse_repository():
            print("\nError: Failed to parse AEGIS repository")
            return 1
        
        print(f"\nSummary:")
        print(f"  - Project: {aegis_repo.project_name}")
        total_changes = sum(len(changes) for changes in aegis_repo.branches.values())
        print(f"  - Total changes: {total_changes}")
        print(f"  - Branches: {len(aegis_repo.branches)}")
        
        # Step 2: Initialize Git repository
        print("\n[Step 2/3] Initializing Git repository...")
        git_importer = GitImporter(args.output, args.force, args.verbose)
        if not git_importer.initialize_repository():
            return 1
        
        # Step 3: Import changes
        print("\n[Step 3/3] Importing changes...")
        if not git_importer.import_changes(aegis_repo):
            return 1
        
        # Success
        print("\n" + "=" * 60)
        print("SUCCESS! Repository imported successfully.")
        print("=" * 60)
        print(f"\nYou can now use your Git repository at: {args.output}")
        print("\nNext steps:")
        print(f"  cd {args.output}")
        print("  git log --all --graph --oneline")
        print("  git branch -a")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
