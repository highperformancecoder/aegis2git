# AEGIS to Git Import Examples

This directory contains example AEGIS repositories for testing and demonstrating the aegis2git.py import tool.

## Sample AEGIS Repository

The `sample-aegis-repo` directory contains a complete sample AEGIS repository with:

- **Project configuration**: `aegis.conf`
- **Change history**: Three changes in the `history/` directory
- **Source code**: Python files in the `src/` directory
- **Multiple branches**: Changes on both master and feature-branch

### Structure

```
sample-aegis-repo/
├── aegis.conf              # AEGIS project configuration
├── README.txt              # Project readme
├── history/                # History directory with change files
│   ├── change001.ae       # Change #1: Initial setup (master)
│   ├── change002.ae       # Change #2: Core module (master)
│   └── change003.ae       # Change #3: Experimental (feature-branch)
└── src/                    # Source code directory
    ├── main.py            # Main application
    ├── core.py            # Core functionality
    ├── utils.py           # Utilities
    └── experimental.py    # Experimental features
```

### Testing the Import

To test the import with this sample repository:

```bash
# From the aegis2git directory
python3 aegis2git.py -i examples/sample-aegis-repo -o /tmp/sample-git-repo
```

### Verifying the Results

After import, verify the Git repository:

```bash
cd /tmp/sample-git-repo

# View commit history
git log --all --graph --oneline --decorate

# List branches
git branch -a

# View detailed commit information
git log --all --format="%H|%an|%ad|%s" --date=iso

# Check out different branches
git checkout master
git checkout feature-branch
```

### Expected Results

The imported Git repository should have:

1. **Two branches**:
   - `master`: Contains changes #1 and #2
   - `feature-branch`: Contains change #3

2. **Three commits** with:
   - Preserved author names (alice, bob, charlie)
   - Preserved dates (2024-01-10 through 2024-01-12)
   - Original commit messages
   - AEGIS change number annotations

3. **All source files** properly imported

## Creating Your Own Test Repository

You can create your own AEGIS test repository by following this structure:

1. Create project configuration file (`aegis.conf`)
2. Create a `history/` directory
3. Add change files (e.g., `change001.ae`, `change002.ae`)
4. Include your source files

### Change File Format

Each change file should contain:

```
change_number = <number>;
description = "<commit message>";
developer = "<author>";
date = "YYYY-MM-DD HH:MM:SS";
branch = "<branch-name>";
file = "<path/to/file>";
```

Example:

```
change_number = 1;
description = "Initial commit";
developer = "john.doe";
date = "2024-01-15 10:30:00";
branch = "master";
file = "README.md";
file = "src/main.py";
```

## Troubleshooting

If the import doesn't work as expected:

1. Check that your AEGIS repository structure matches the expected format
2. Verify that change files have correct syntax
3. Use the `-v` (verbose) flag for detailed output:
   ```bash
   python3 aegis2git.py -i examples/sample-aegis-repo -o /tmp/test -v
   ```

## Additional Resources

See the main [README.md](../README.md) for complete documentation on:
- Installation
- Usage
- Command-line options
- Troubleshooting
