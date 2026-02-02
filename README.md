# AEGIS to Git Import Tool

A Python script to import AEGIS source code repositories into Git repositories, preserving the original branch structure and commit comments.

## Overview

AEGIS (Automated Electronic Generation of Information Systems) is a legacy configuration management system that predates modern version control systems like Git. This tool helps organizations migrate their historical AEGIS repositories to Git, making them compatible with modern development workflows and tools.

### Key Features

- **Branch Preservation**: Maintains the original branch structure from AEGIS
- **Commit History**: Preserves commit messages, authors, and timestamps
- **Automatic Detection**: Intelligently detects AEGIS repository structure
- **Flexible Import**: Supports various AEGIS repository formats and structures
- **Progress Tracking**: Provides detailed feedback during the import process

## Prerequisites

### System Requirements

- Python 3.6 or higher
- Git 2.x or higher
- Access to the AEGIS repository you want to import

### Checking Your System

```bash
# Check Python version
python3 --version

# Check Git version
git --version
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/highperformancecoder/aegis2git.git
cd aegis2git
```

2. Make the script executable (optional):
```bash
chmod +x aegis2git.py
```

## Usage

### Basic Usage

```bash
python3 aegis2git.py -i /path/to/aegis/repo -o /path/to/git/repo
```

### Command-Line Options

| Option | Long Form | Description |
|--------|-----------|-------------|
| `-i` | `--input` | Path to the AEGIS source repository (required) |
| `-o` | `--output` | Path to the target Git repository (required) |
| `-f` | `--force` | Force reinitialization of existing Git repository |
| `-v` | `--verbose` | Enable verbose output for debugging |
| | `--version` | Show version information |
| `-h` | `--help` | Show help message |

### Examples

#### Example 1: Basic Import

Import an AEGIS repository to a new Git repository:

```bash
python3 aegis2git.py -i ~/old-projects/aegis-repo -o ~/new-projects/git-repo
```

#### Example 2: Force Reinitialize

Force reinitialization of an existing Git repository:

```bash
python3 aegis2git.py -i ./aegis-project -o ./git-project --force
```

⚠️ **Warning**: The `--force` flag will delete the existing Git repository and start fresh!

#### Example 3: Verbose Output

Run with verbose output for debugging or detailed information:

```bash
python3 aegis2git.py -i /data/aegis/myproject -o /data/git/myproject -v
```

## How It Works

The import process follows three main steps:

### Step 1: Parse AEGIS Repository

The script scans the AEGIS repository to:
- Identify the project structure
- Extract change history
- Parse commit information (descriptions, authors, dates)
- Map branch relationships

### Step 2: Initialize Git Repository

The script:
- Creates the target Git repository directory (if needed)
- Initializes a new Git repository
- Sets up the initial branch structure

### Step 3: Import Changes

For each AEGIS change:
- Copies relevant files to the Git repository
- Creates a Git commit with preserved metadata
- Maintains branch relationships
- Preserves commit messages and author information

## AEGIS Repository Structure

The script can handle various AEGIS repository structures, including:

- **Standard AEGIS repositories**: With `aegis.conf` or `project.conf`
- **History directories**: `history/`, `baseline/`, `delta/`, or `changes/`
- **Change files**: Numbered change files or directories
- **Custom structures**: The script attempts to intelligently detect patterns

## Expected Output

After a successful import, you'll see:

```
============================================================
AEGIS to Git Repository Import Tool
============================================================
Input AEGIS repository: /path/to/aegis/repo
Output Git repository:  /path/to/git/repo
============================================================

[Step 1/3] Parsing AEGIS repository...
Found AEGIS project: myproject
Found history directory: history
  Parsed change #1: Initial project setup...
  Parsed change #2: Added core functionality...
  ...

Summary:
  - Project: myproject
  - Changes: 42
  - Branches: 2

[Step 2/3] Initializing Git repository...
Git repository initialized successfully.

[Step 3/3] Importing changes...
============================================================
Starting import of AEGIS changes to Git
============================================================

Importing primary branch: master
  Importing change #1: Initial project setup...
    ✓ Committed change #1
  Importing change #2: Added core functionality...
    ✓ Committed change #2
  ...

============================================================
Import completed successfully!
============================================================

SUCCESS! Repository imported successfully.
============================================================

You can now use your Git repository at: /path/to/git/repo

Next steps:
  cd /path/to/git/repo
  git log --all --graph --oneline
  git branch -a
```

## Verifying the Import

After the import completes, verify the results:

### 1. Check Commit History

```bash
cd /path/to/git/repo
git log --all --graph --oneline
```

### 2. View All Branches

```bash
git branch -a
```

### 3. Inspect a Specific Commit

```bash
git show <commit-hash>
```

### 4. Check Repository Statistics

```bash
git log --all --oneline | wc -l  # Count commits
git branch | wc -l                # Count branches
```

## Troubleshooting

### Issue: "AEGIS repository path does not exist"

**Solution**: Verify the path to your AEGIS repository is correct:
```bash
ls -la /path/to/aegis/repo
```

### Issue: "No changes found in AEGIS repository"

**Possible causes**:
- The AEGIS repository structure is non-standard
- The repository is empty or incomplete

**Solution**: 
- Check if the repository contains history files
- Use the `-v` flag for verbose output to see what's being detected
- The script will create an initial synthetic commit if no changes are found

### Issue: "Git repository already exists"

**Solution**: Use the `--force` flag to reinitialize:
```bash
python3 aegis2git.py -i /path/to/aegis -o /path/to/git --force
```

### Issue: "Permission denied"

**Solution**: Ensure you have read access to the AEGIS repository and write access to the target directory:
```bash
# Check AEGIS permissions
ls -la /path/to/aegis/repo

# Check target directory permissions
mkdir -p /path/to/git/repo
ls -la /path/to/git/
```

### Issue: Git commands fail

**Solution**: Ensure Git is installed and accessible:
```bash
git --version
which git
```

## Advanced Usage

### Importing Specific Branches

Currently, the script imports all branches automatically. To work with specific branches after import:

```bash
cd /path/to/git/repo

# List all branches
git branch -a

# Checkout a specific branch
git checkout branch-name

# Delete unwanted branches
git branch -d branch-name
```

### Customizing Author Information

After import, you can update author information using Git's filter-branch or filter-repo tools:

```bash
# Update author email for all commits
git filter-branch --env-filter '
if [ "$GIT_AUTHOR_EMAIL" = "olduser@aegis" ]; then
    export GIT_AUTHOR_EMAIL="newuser@example.com"
fi
' --tag-name-filter cat -- --all
```

### Cleaning Up AEGIS Artifacts

If the import includes AEGIS-specific files you don't want in Git:

```bash
cd /path/to/git/repo

# Remove unwanted files
git rm -r history/
git rm aegis.conf

# Commit the cleanup
git commit -m "Remove AEGIS artifacts"
```

## Limitations

- **Binary Files**: Large binary files might not be handled optimally
- **Complex Branching**: Highly complex branch structures might require manual verification
- **Timestamps**: If AEGIS timestamps are malformed, current time will be used
- **Custom AEGIS Configurations**: Non-standard AEGIS setups might need script modifications

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/highperformancecoder/aegis2git.git
cd aegis2git

# Make changes and test
python3 aegis2git.py -i test/aegis-repo -o test/git-repo -v
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter issues or have questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Run with `--verbose` flag for detailed output
3. Open an issue on GitHub with:
   - Your Python and Git versions
   - The complete error message
   - A description of your AEGIS repository structure (if possible)

## Acknowledgments

This tool was created to help organizations preserve their development history when migrating from legacy AEGIS systems to modern Git-based workflows.

## Version History

- **1.0.0** (2024): Initial release
  - Basic AEGIS to Git import functionality
  - Branch and commit preservation
  - Command-line interface
  - Comprehensive documentation
