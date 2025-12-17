# GitHub Repository LOC Statistics Tool

This Python script retrieves Lines of Code (LOC) statistics for a specific GitHub repository and username starting from a specified date (default: 2025-01-01). It calculates the total changes (additions + deletions) for commits by the specified author.

## Features

- Fetches commits by a specific author from a GitHub repository
- Filters commits by start date (default: 2025-01-01)
- Calculates total additions, deletions, and combined changes
- Provides detailed commit-by-commit statistics
- Supports GitHub API token for higher rate limits
- Exports results to JSON format
- Shows top commits by number of changes

## Prerequisites

```bash
pip install requests
```

### Set Github Personal Access Token
```bash
export GITHUB_TOKEN=<your_pat_github_token>
```

## Usage

### Basic Usage
```bash
python3 get_repo_loc_stats.py <repo_owner> <repo_name> <author_username>
```

### With Custom Start Date
```bash
python3 get_repo_loc_stats.py <repo_owner> <repo_name> <author_username> --start-date 2024-06-01
```

### Save Results to JSON File
```bash
python3 get_repo_loc_stats.py <repo_owner> <repo_name> <author_username> --output results.json
```

### Get PRs on Specific Repo
```bash
python3 get_repo_prs.py <repo_owner> <repo_name> <author_username> --start-date 2025-01-01
```

## Examples

### Example 1: Analyze a user's contributions to a repository and save result
```bash
python3 get_repo_loc_stats.py microsoft vscode username --start-date 2025-01-01 --output react_stats.json
```


## Output

The script provides:

1. **Summary Statistics:**
   - Repository name
   - Author username
   - Analysis period
   - Total commits
   - Total additions (lines added)
   - Total deletions (lines removed)
   - Total changes (additions + deletions)
   - Average changes per commit

2. **Top 10 commits** by number of changes

3. **Detailed JSON output** (if --output specified) with:
   - Complete commit list with individual statistics
   - Commit messages, dates, and SHA hashes
   - Per-commit additions, deletions, and total changes

## GitHub Token Setup

For better rate limits (5000 requests/hour vs 60), create a GitHub personal access token:

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate a new token with `public_repo` scope (for public repositories)
3. Use the token with the `--token` parameter

## Rate Limits

- **Without token:** 60 requests per hour
- **With token:** 5000 requests per hour

## Error Handling

The script handles common scenarios:
- Repository not found or not accessible
- API rate limit exceeded
- Network connectivity issues
- Invalid date formats
- Missing commits or statistics

## Sample Output

```
Analyzing LOC for repository: microsoft/vscode
Author: username
Start date: 2025-01-01
--------------------------------------------------

Found 25 commits by username since 2025-01-01T00:00:00+00:00
Fetching detailed statistics for 25 commits...

============================================================
LOC ANALYSIS SUMMARY
============================================================
Repository: microsoft/vscode
Author: username
Analysis period: From 2025-01-01 to present
Total commits: 25
------------------------------------------------------------
Total additions: 1,245 lines
Total deletions: 387 lines
Total changes: 1,632 lines
------------------------------------------------------------
Average changes per commit: 65.3 lines

Top 10 commits by changes:
 1. a1b2c3d4 ( 234 changes) - Add new feature for syntax highlighting...
 2. e5f6g7h8 ( 189 changes) - Refactor editor component architecture...
 3. i9j0k1l2 ( 156 changes) - Fix memory leak in extension host...
```