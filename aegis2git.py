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
        self.changes = []
        self.branches = {}
        
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
        
        # Try to find AEGIS project configuration
        config_files = ['aegis.conf', 'project.conf', '.aegis']
        config_path = None
        
        for config_file in config_files:
            potential_path = self.aegis_path / config_file
            if potential_path.exists():
                config_path = potential_path
                break
        
        if config_path:
            self.project_name = self._extract_project_name(config_path)
            print(f"Found AEGIS project: {self.project_name}")
        else:
            # Use directory name as fallback
            self.project_name = self.aegis_path.name
            print(f"No AEGIS config found, using directory name: {self.project_name}")
        
        # Extract history information from AEGIS repository structure
        self._extract_changes()
        self._extract_branches()
        
        return len(self.changes) > 0
    
    def _extract_project_name(self, config_path: Path) -> str:
        """
        Extract project name from AEGIS configuration file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Project name
        """
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Look for project name in various formats
                match = re.search(r'project[_\s]*name\s*[=:]\s*["\']?([^"\'\s;]+)', content, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"Warning: Could not parse config file: {e}")
        
        return "aegis-project"
    
    def _extract_changes(self):
        """
        Extract change history from AEGIS repository.
        
        AEGIS typically stores changes in numbered directories or files.
        This method attempts to discover and parse them.
        """
        # Look for common AEGIS history structures
        history_dirs = ['history', 'baseline', 'delta', 'changes']
        
        for hist_dir in history_dirs:
            hist_path = self.aegis_path / hist_dir
            if hist_path.exists() and hist_path.is_dir():
                print(f"Found history directory: {hist_dir}")
                self._scan_history_directory(hist_path)
        
        # If no history directory found, scan for numbered change files
        if not self.changes:
            self._scan_root_for_changes()
        
        # Sort changes by timestamp or change number
        self.changes.sort(key=lambda x: x['number'])
        
        if not self.changes:
            print("Warning: No changes found in AEGIS repository")
            # Create a synthetic initial change for empty repositories
            self._create_initial_change()
    
    def _scan_history_directory(self, hist_path: Path):
        """
        Scan a history directory for AEGIS changes.
        
        Args:
            hist_path: Path to the history directory
        """
        for entry in sorted(hist_path.iterdir()):
            if entry.is_file():
                # Try to extract change number from filename
                match = re.search(r'(\d+)', entry.name)
                if match:
                    change_num = int(match.group(1))
                    self._parse_change_file(entry, change_num)
            elif entry.is_dir():
                # Recursively scan subdirectories
                self._scan_history_directory(entry)
    
    def _scan_root_for_changes(self):
        """Scan root directory for AEGIS change markers."""
        # Look for files that might contain change information
        for entry in self.aegis_path.iterdir():
            if entry.is_file():
                name = entry.name.lower()
                if 'change' in name or 'history' in name or name.endswith('.ae'):
                    try:
                        match = re.search(r'(\d+)', entry.name)
                        if match:
                            change_num = int(match.group(1))
                            self._parse_change_file(entry, change_num)
                    except Exception:
                        pass
    
    def _parse_change_file(self, file_path: Path, change_num: int):
        """
        Parse an AEGIS change file.
        
        Args:
            file_path: Path to the change file
            change_num: Change number
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract change information
            change_info = {
                'number': change_num,
                'file': str(file_path),
                'description': self._extract_description(content),
                'author': self._extract_author(content),
                'date': self._extract_date(content),
                'branch': self._extract_branch(content),
                'files': self._extract_files(content)
            }
            
            self.changes.append(change_info)
            print(f"  Parsed change #{change_num}: {change_info['description'][:50]}...")
            
        except Exception as e:
            print(f"Warning: Could not parse change file {file_path}: {e}")
    
    def _extract_description(self, content: str) -> str:
        """Extract commit description from AEGIS change content."""
        # Look for common description patterns
        patterns = [
            r'description\s*[=:]\s*["\']([^"\']+)["\']',
            r'brief_description\s*[=:]\s*["\']([^"\']+)["\']',
            r'summary\s*[=:]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return f"AEGIS change (no description found)"
    
    def _extract_author(self, content: str) -> str:
        """Extract author information from AEGIS change content."""
        patterns = [
            r'developer\s*[=:]\s*["\']?([^"\';\s]+)',
            r'author\s*[=:]\s*["\']?([^"\';\s]+)',
            r'user\s*[=:]\s*["\']?([^"\';\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "aegis-user"
    
    def _extract_date(self, content: str) -> str:
        """Extract date information from AEGIS change content."""
        # Look for date patterns
        patterns = [
            r'date\s*[=:]\s*["\']?([^"\';\n]+)',
            r'timestamp\s*[=:]\s*["\']?([^"\';\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Try to parse and standardize the date
                return self._normalize_date(date_str)
        
        # Use current time as fallback
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to standard format.
        
        Args:
            date_str: Date string from AEGIS
            
        Returns:
            Normalized date string
        """
        # Try various date formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d',
            '%d-%b-%Y',
            '%Y%m%d%H%M%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        # If parsing fails, return original
        return date_str
    
    def _extract_branch(self, content: str) -> str:
        """Extract branch information from AEGIS change content."""
        patterns = [
            r'branch\s*[=:]\s*["\']?([^"\';\s]+)',
            r'baseline\s*[=:]\s*["\']?([^"\';\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "master"
    
    def _extract_files(self, content: str) -> List[str]:
        """Extract list of files modified in this change."""
        files = []
        
        # Look for file lists
        patterns = [
            r'file\s*[=:]\s*["\']([^"\']+)["\']',
            r'src\s*[=:]\s*["\']([^"\']+)["\']',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                files.append(match.group(1))
        
        return files
    
    def _extract_branches(self):
        """Extract branch structure from AEGIS repository."""
        # Group changes by branch
        for change in self.changes:
            branch = change['branch']
            if branch not in self.branches:
                self.branches[branch] = []
            self.branches[branch].append(change)
        
        print(f"\nFound {len(self.branches)} branch(es): {', '.join(self.branches.keys())}")
    
    def _create_initial_change(self):
        """Create a synthetic initial change for empty repositories."""
        self.changes.append({
            'number': 0,
            'file': '',
            'description': 'Initial import from AEGIS',
            'author': 'aegis-user',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'branch': 'master',
            'files': []
        })
    
    def get_changes(self) -> List[Dict]:
        """Get list of all changes."""
        return self.changes
    
    def get_branches(self) -> Dict[str, List[Dict]]:
        """Get branch structure with changes."""
        return self.branches


class GitImporter:
    """Class to handle Git repository import operations."""
    
    def __init__(self, git_path: str, force: bool = False):
        """
        Initialize Git importer.
        
        Args:
            git_path: Path to the target Git repository
            force: If True, reinitialize existing repository
        """
        self.git_path = Path(git_path).resolve()
        self.force = force
        
    def initialize_repository(self) -> bool:
        """
        Initialize or verify Git repository.
        
        Returns:
            True if successful, False otherwise
        """
        print(f"\nInitializing Git repository at: {self.git_path}")
        
        # Create directory if it doesn't exist
        self.git_path.mkdir(parents=True, exist_ok=True)
        
        git_dir = self.git_path / '.git'
        
        if git_dir.exists():
            if self.force:
                print("Warning: Git repository already exists. Reinitializing...")
                shutil.rmtree(git_dir)
            else:
                print("Git repository already exists.")
                return True
        
        # Initialize Git repository
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
            aegis_repo: AegisRepository instance with parsed data
            
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*60)
        print("Starting import of AEGIS changes to Git")
        print("="*60)
        
        branches = aegis_repo.get_branches()
        
        # Import master/main branch first
        master_branch = None
        for branch_name in ['master', 'main', 'trunk', 'baseline']:
            if branch_name in branches:
                master_branch = branch_name
                break
        
        if not master_branch and branches:
            # Use first available branch as master
            master_branch = list(branches.keys())[0]
        
        if master_branch:
            print(f"\nImporting primary branch: {master_branch}")
            self._import_branch(master_branch, branches[master_branch], aegis_repo, is_primary=True)
        
        # Import other branches
        for branch_name, changes in branches.items():
            if branch_name != master_branch:
                print(f"\nImporting branch: {branch_name}")
                self._import_branch(branch_name, changes, aegis_repo, is_primary=False, primary_branch=master_branch)
        
        print("\n" + "="*60)
        print("Import completed successfully!")
        print("="*60)
        
        return True
    
    def _import_branch(self, branch_name: str, changes: List[Dict], aegis_repo: AegisRepository, 
                       is_primary: bool = False, primary_branch: Optional[str] = None):
        """
        Import a specific branch with its changes.
        
        Args:
            branch_name: Name of the branch
            changes: List of changes for this branch
            aegis_repo: AegisRepository instance
            is_primary: Whether this is the primary/master branch
            primary_branch: Name of the primary branch (for creating feature branches from)
        """
        # Create and checkout branch
        try:
            # Check if this is the first commit
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.git_path,
                capture_output=True
            )
            has_commits = result.returncode == 0
            
            if has_commits and not is_primary:
                # Create new branch from primary branch
                if primary_branch:
                    subprocess.run(
                        ['git', 'checkout', primary_branch],
                        cwd=self.git_path,
                        capture_output=True
                    )
                subprocess.run(
                    ['git', 'checkout', '-b', branch_name],
                    cwd=self.git_path,
                    check=True,
                    capture_output=True
                )
            elif not has_commits:
                # First commit, just use current branch
                if not is_primary:
                    # Rename to desired branch
                    subprocess.run(
                        ['git', 'branch', '-M', branch_name],
                        cwd=self.git_path,
                        capture_output=True
                    )
            else:
                # Checkout existing branch
                subprocess.run(
                    ['git', 'checkout', branch_name],
                    cwd=self.git_path,
                    capture_output=True
                )
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not create/checkout branch {branch_name}: {e}")
        
        # Import each change as a commit
        for change in changes:
            self._import_change(change, aegis_repo)
    
    def _import_change(self, change: Dict, aegis_repo: AegisRepository):
        """
        Import a single AEGIS change as a Git commit.
        
        Args:
            change: Change information dictionary
            aegis_repo: AegisRepository instance
        """
        change_num = change['number']
        description = change['description']
        author = change['author']
        date = change['date']
        files = change['files']
        
        print(f"  Importing change #{change_num}: {description[:60]}...")
        
        # Copy files from AEGIS repository to Git repository
        if files:
            for file_path in files:
                src = aegis_repo.aegis_path / file_path
                if src.exists():
                    dst = self.git_path / file_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
        else:
            # If no specific files, copy all non-git content
            self._copy_repository_content(aegis_repo.aegis_path)
        
        # Stage all changes
        try:
            subprocess.run(
                ['git', 'add', '-A'],
                cwd=self.git_path,
                check=True,
                capture_output=True
            )
            
            # Check if there are any changes to commit
            result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                cwd=self.git_path,
                capture_output=True
            )
            
            if result.returncode != 0:  # There are changes
                # Create commit with preserved metadata
                commit_message = f"{description}\n\nAEGIS change #{change_num}"
                
                env = os.environ.copy()
                env['GIT_AUTHOR_NAME'] = author
                env['GIT_AUTHOR_EMAIL'] = f"{author}@aegis"
                env['GIT_AUTHOR_DATE'] = date
                env['GIT_COMMITTER_NAME'] = author
                env['GIT_COMMITTER_EMAIL'] = f"{author}@aegis"
                env['GIT_COMMITTER_DATE'] = date
                
                subprocess.run(
                    ['git', 'commit', '-m', commit_message],
                    cwd=self.git_path,
                    env=env,
                    check=True,
                    capture_output=True
                )
                print(f"    ✓ Committed change #{change_num}")
            else:
                print(f"    ⊘ No changes to commit for #{change_num}")
                
        except subprocess.CalledProcessError as e:
            print(f"    ✗ Error committing change #{change_num}: {e}")
    
    def _copy_repository_content(self, source_path: Path):
        """
        Copy all content from source to Git repository, excluding version control files.
        
        Args:
            source_path: Source AEGIS repository path
        """
        for item in source_path.rglob('*'):
            # Skip version control directories and hidden files
            if any(part.startswith('.') for part in item.parts):
                continue
            
            # Skip AEGIS-specific directories
            if any(part in ['history', 'baseline', 'delta'] for part in item.parts):
                continue
            
            if item.is_file():
                rel_path = item.relative_to(source_path)
                dst = self.git_path / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(item, dst)
                except Exception as e:
                    print(f"    Warning: Could not copy {rel_path}: {e}")


def main():
    """Main entry point for the script."""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Import an AEGIS source code repository into Git',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i /path/to/aegis/repo -o /path/to/git/repo
  %(prog)s --input ./aegis-project --output ./git-project --force
  %(prog)s -i ~/projects/old-aegis -o ~/projects/new-git -v

For more information, see the README.md file.
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        dest='aegis_path',
        required=True,
        help='Path to the AEGIS source repository'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='git_path',
        required=True,
        help='Path to the target Git repository (will be created if it does not exist)'
    )
    
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force reinitialization of existing Git repository'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Display header
    print("="*60)
    print("AEGIS to Git Repository Import Tool")
    print("="*60)
    print(f"Input AEGIS repository: {args.aegis_path}")
    print(f"Output Git repository:  {args.git_path}")
    print("="*60)
    
    try:
        # Step 1: Parse AEGIS repository
        print("\n[Step 1/3] Parsing AEGIS repository...")
        aegis_repo = AegisRepository(args.aegis_path)
        
        if not aegis_repo.parse_repository():
            print("Error: Could not parse AEGIS repository")
            return 1
        
        changes = aegis_repo.get_changes()
        branches = aegis_repo.get_branches()
        
        print(f"\nSummary:")
        print(f"  - Project: {aegis_repo.project_name}")
        print(f"  - Changes: {len(changes)}")
        print(f"  - Branches: {len(branches)}")
        
        # Step 2: Initialize Git repository
        print("\n[Step 2/3] Initializing Git repository...")
        git_importer = GitImporter(args.git_path, force=args.force)
        
        if not git_importer.initialize_repository():
            print("Error: Could not initialize Git repository")
            return 1
        
        # Step 3: Import changes
        print("\n[Step 3/3] Importing changes...")
        if not git_importer.import_changes(aegis_repo):
            print("Error: Could not import changes")
            return 1
        
        # Success
        print("\n" + "="*60)
        print("SUCCESS! Repository imported successfully.")
        print("="*60)
        print(f"\nYou can now use your Git repository at: {args.git_path}")
        print("\nNext steps:")
        print("  cd " + args.git_path)
        print("  git log --all --graph --oneline")
        print("  git branch -a")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
