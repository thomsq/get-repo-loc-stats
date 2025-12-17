#!/usr/bin/env python3
"""
GitHub Repository Pull Request File Changes Analyzer

This script retrieves all Pull Requests for a specific repository and username,
then fetches detailed file changes for each PR including:
- Files modified, added, deleted
- Lines added/deleted per file
- Actual diff/patch content (optional)

IMPORTANT: GitHub Personal Access Token (PAT) Required
============================================
To use this tool effectively, you need a GitHub Personal Access Token:

1. Go to GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: 'repo' (for private repos) or 'public_repo' (for public repos only)
4. Copy the generated token
5. Use it with the --token parameter or set it as an environment variable

Without a PAT, you'll be limited to 60 API requests per hour and may not access private repositories.
"""

import requests
import json
from datetime import datetime, timezone
import argparse
import sys
import os
from typing import Dict, List, Optional


class GitHubPRFileAnalyzer:
    """GitHub repository Pull Request file changes analyzer"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub PR file analyzer
        
        Args:
            token: GitHub personal access token (required for reliable operation)
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        if not self.token:
            print("⚠️  WARNING: No GitHub Personal Access Token provided!")
            print("   You'll be limited to 60 requests/hour and cannot access private repos.")
            print("   Get a PAT at: https://github.com/settings/tokens")
            print("   Use --token parameter or set GITHUB_TOKEN environment variable\n")
        
        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def get_pull_requests(self, repo_owner: str, repo_name: str, author: str, since_date: str, state: str = "all", merged_only: bool = True, include_draft: bool = False) -> List[Dict]:
        """
        Get pull requests by a specific author since the given date
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to filter PRs
            since_date: ISO format date string (e.g., '2025-01-01T00:00:00Z')
            state: PR state filter ('open', 'closed', 'all')
            merged_only: Filter to only merged PRs (default: True)
            include_draft: Include draft PRs (default: False)
            
        Returns:
            List of pull request objects
        """
        pull_requests = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls"
            params = {
                'state': state,
                'per_page': per_page,
                'page': page,
                'sort': 'created',
                'direction': 'desc'
            }
            
            print(f"Fetching PRs page {page}...")
            response = self.session.get(url, params=params)
            
            if response.status_code == 404:
                print(f"Error: Repository {repo_owner}/{repo_name} not found or not accessible")
                return []
            elif response.status_code == 403:
                error_msg = "Error: API rate limit exceeded or access forbidden"
                if not self.token:
                    error_msg += "\n💡 Try using a GitHub Personal Access Token with --token parameter"
                    error_msg += "\n   Get one at: https://github.com/settings/tokens"
                print(error_msg)
                return []
            elif response.status_code != 200:
                print(f"Error fetching PRs: {response.status_code} - {response.text}")
                return []
            
            page_prs = response.json()
            if not page_prs:
                break
            
            # Filter PRs by author and date
            filtered_prs = []
            for pr in page_prs:
                # Check if PR is by the specified author
                if pr['user']['login'].lower() == author.lower():
                    # Check if PR was created after the specified date
                    created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                    since_datetime = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                    
                    if created_at >= since_datetime:
                        # Filter by merged status if merged_only is True
                        if merged_only and not pr.get('merged_at'):
                            continue
                        
                        # Filter out draft PRs unless include_draft is True
                        if not include_draft and pr.get('draft', False):
                            continue
                        
                        filtered_prs.append(pr)
                    else:
                        # Since PRs are sorted by creation date (desc), we can stop here
                        return pull_requests
            
            pull_requests.extend(filtered_prs)
            page += 1
            
            # GitHub API pagination limit check
            if len(page_prs) < per_page:
                break
        
        filter_desc = []
        if merged_only:
            filter_desc.append("merged")
        if not include_draft:
            filter_desc.append("non-draft")
        filter_text = " ".join(filter_desc) if filter_desc else "all"
        print(f"Found {len(pull_requests)} {filter_text} PRs by {author} since {since_date}")
        return pull_requests
    
    def get_pr_files(self, repo_owner: str, repo_name: str, pr_number: int, include_patch: bool = False) -> List[Dict]:
        """
        Get list of files changed in a specific pull request
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            pr_number: Pull request number
            include_patch: Whether to include patch/diff content
            
        Returns:
            List of file change objects
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/files"
        files = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                'per_page': per_page,
                'page': page
            }
            
            response = self.session.get(url, params=params)
            
            if response.status_code != 200:
                print(f"Warning: Could not fetch files for PR #{pr_number}: {response.status_code}")
                return []
            
            page_files = response.json()
            if not page_files:
                break
            
            for file in page_files:
                file_info = {
                    'filename': file['filename'],
                    'status': file['status'],  # added, removed, modified, renamed
                    'additions': file['additions'],
                    'deletions': file['deletions'],
                    'changes': file['changes'],
                    'blob_url': file.get('blob_url'),
                    'raw_url': file.get('raw_url'),
                    'contents_url': file.get('contents_url')
                }
                
                # Include patch if requested (can be large)
                if include_patch and 'patch' in file:
                    file_info['patch'] = file['patch']
                
                # Include previous filename if renamed
                if file['status'] == 'renamed' and 'previous_filename' in file:
                    file_info['previous_filename'] = file['previous_filename']
                
                files.append(file_info)
            
            page += 1
            
            # GitHub API pagination limit check
            if len(page_files) < per_page:
                break
        
        return files
    
    def analyze_pr_file_changes(self, repo_owner: str, repo_name: str, author: str, 
                                start_date: str = "2025-01-01", state: str = "all",
                                include_patch: bool = False, limit: Optional[int] = None,
                                merged_only: bool = True, include_draft: bool = False) -> Dict:
        """
        Analyze file changes for Pull Requests in a repository
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to analyze
            start_date: Start date in YYYY-MM-DD format
            state: PR state filter ('open', 'closed', 'all')
            include_patch: Whether to include patch/diff content
            limit: Limit number of PRs to analyze (None for all)
            merged_only: Filter to only merged PRs (default: True)
            include_draft: Include draft PRs (default: False)
            
        Returns:
            Dictionary containing PR file change statistics
        """
        # Convert start_date to ISO format
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            since_date = start_datetime.isoformat()
        except ValueError:
            print(f"Error: Invalid date format '{start_date}'. Please use YYYY-MM-DD format.")
            return {}
        
        print(f"\nAnalyzing Pull Request file changes for repository: {repo_owner}/{repo_name}")
        print(f"Author: {author}")
        print(f"Start date: {start_date}")
        print(f"State filter: {state}")
        print(f"Merged only: {merged_only}")
        print(f"Include draft: {include_draft}")
        print(f"Include patches: {include_patch}")
        if limit:
            print(f"PR limit: {limit}")
        print("-" * 70)
        
        # Get pull requests
        prs = self.get_pull_requests(repo_owner, repo_name, author, since_date, state, merged_only, include_draft)
        
        if not prs:
            return {
                'repository': f"{repo_owner}/{repo_name}",
                'author': author,
                'start_date': start_date,
                'state_filter': state,
                'total_prs': 0,
                'pull_requests': []
            }
        
        # Limit PRs if specified
        if limit:
            prs = prs[:limit]
            print(f"Limiting analysis to {len(prs)} most recent PRs")
        
        pr_file_details = []
        total_files_changed = 0
        total_additions = 0
        total_deletions = 0
        file_extension_stats = {}
        
        print(f"\nProcessing {len(prs)} pull requests...")
        
        for i, pr in enumerate(prs, 1):
            print(f"\nProcessing PR {i}/{len(prs)}: #{pr['number']} - {pr['title'][:50]}...")
            
            # Get files changed in this PR
            files = self.get_pr_files(repo_owner, repo_name, pr['number'], include_patch)
            
            if files:
                print(f"  Found {len(files)} files changed")
                total_files_changed += len(files)
                
                pr_additions = sum(f['additions'] for f in files)
                pr_deletions = sum(f['deletions'] for f in files)
                total_additions += pr_additions
                total_deletions += pr_deletions
                
                # Track file extensions
                for file in files:
                    ext = os.path.splitext(file['filename'])[1] or 'no_extension'
                    if ext not in file_extension_stats:
                        file_extension_stats[ext] = {
                            'count': 0,
                            'additions': 0,
                            'deletions': 0
                        }
                    file_extension_stats[ext]['count'] += 1
                    file_extension_stats[ext]['additions'] += file['additions']
                    file_extension_stats[ext]['deletions'] += file['deletions']
            
            # Extract PR information with file details
            pr_info = {
                'number': pr['number'],
                'title': pr['title'],
                'state': pr['state'],
                'draft': pr.get('draft', False),
                'created_at': pr['created_at'],
                'updated_at': pr['updated_at'],
                'closed_at': pr.get('closed_at'),
                'merged_at': pr.get('merged_at'),
                'html_url': pr['html_url'],
                'total_files_changed': len(files),
                'total_additions': pr_additions,
                'total_deletions': pr_deletions,
                'files': files
            }
            
            pr_file_details.append(pr_info)
        
        # Sort PRs by number (descending)
        pr_file_details.sort(key=lambda x: x['number'], reverse=True)
        
        # Sort file extension stats by count
        sorted_ext_stats = dict(sorted(file_extension_stats.items(), 
                                      key=lambda x: x[1]['count'], 
                                      reverse=True))
        
        results = {
            'repository': f"{repo_owner}/{repo_name}",
            'author': author,
            'start_date': start_date,
            'state_filter': state,
            'merged_only': merged_only,
            'include_draft': include_draft,
            'total_prs': len(prs),
            'total_files_changed': total_files_changed,
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'file_extension_stats': sorted_ext_stats,
            'pull_requests': pr_file_details
        }
        
        return results
    
    def print_summary(self, results: Dict):
        """Print a formatted summary of the results"""
        if not results:
            print("No results to display.")
            return
        
        print("\n" + "=" * 70)
        print("PULL REQUEST FILE CHANGES ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Repository: {results['repository']}")
        print(f"Author: {results['author']}")
        print(f"Analysis period: From {results['start_date']} to present")
        print(f"State filter: {results['state_filter']}")
        print(f"Merged only: {results.get('merged_only', True)}")
        print(f"Include draft: {results.get('include_draft', False)}")
        print("-" * 70)
        print(f"Total PRs analyzed: {results['total_prs']}")
        print(f"Total files changed: {results['total_files_changed']}")
        print(f"Total lines added: {results['total_additions']:,}")
        print(f"Total lines deleted: {results['total_deletions']:,}")
        print(f"Net change: {results['total_additions'] - results['total_deletions']:+,} lines")
        print("-" * 70)
        
        if results['file_extension_stats']:
            print("\nFile Type Statistics (Top 10):")
            print(f"{'Extension':<15} {'Files':<10} {'Added':<12} {'Deleted':<12} {'Net':<12}")
            print("-" * 70)
            for ext, stats in list(results['file_extension_stats'].items())[:10]:
                net_change = stats['additions'] - stats['deletions']
                print(f"{ext:<15} {stats['count']:<10} {stats['additions']:<12,} {stats['deletions']:<12,} {net_change:+<12,}")
        
        print("\n" + "=" * 70)
        print("INDIVIDUAL PR DETAILS")
        print("=" * 70)
        
        for i, pr in enumerate(results['pull_requests'], 1):
            status_emoji = "🟢" if pr['state'] == 'open' else "🔴" if pr['state'] == 'closed' else "⚪"
            merged_text = " (merged)" if pr['merged_at'] else ""
            draft_text = " [DRAFT]" if pr['draft'] else ""
            
            print(f"\n{i}. {status_emoji} PR #{pr['number']}{draft_text}{merged_text}")
            print(f"   Title: {pr['title']}")
            print(f"   URL: {pr['html_url']}")
            print(f"   Files: {pr['total_files_changed']}, Added: +{pr['total_additions']}, Deleted: -{pr['total_deletions']}")
            
            if pr['files']:
                print(f"   Changed files:")
                for file in pr['files'][:20]:  # Limit to first 20 files per PR
                    status_icon = {
                        'added': '➕',
                        'removed': '➖',
                        'modified': '📝',
                        'renamed': '🔄'
                    }.get(file['status'], '❓')
                    
                    change_text = f"+{file['additions']} -{file['deletions']}"
                    print(f"      {status_icon} {file['filename']} ({change_text})")
                
                if len(pr['files']) > 20:
                    print(f"      ... and {len(pr['files']) - 20} more files")


def main():
    """Main function to run the PR file changes analyzer"""
    parser = argparse.ArgumentParser(
        description='Analyze GitHub repository Pull Request file changes',
        epilog='''
GitHub Personal Access Token Required:
  Get a token at: https://github.com/settings/tokens
  Required scopes: 'repo' (private) or 'public_repo' (public only)
  
  Usage options:
  1. Command line: --token YOUR_TOKEN_HERE
  2. Environment: export GITHUB_TOKEN=YOUR_TOKEN_HERE
  
  Without a token, you're limited to 60 requests/hour.''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('repo_owner', help='Repository owner username')
    parser.add_argument('repo_name', help='Repository name')
    parser.add_argument('author', help='Author username to analyze')
    parser.add_argument('--start-date', default='2025-01-01', 
                      help='Start date in YYYY-MM-DD format (default: 2025-01-01)')
    parser.add_argument('--state', choices=['open', 'closed', 'all'], default='all',
                      help='Filter PRs by state (default: all)')
    parser.add_argument('--token', 
                      help='GitHub Personal Access Token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--output', help='Output file path to save results as JSON')
    parser.add_argument('--include-patch', action='store_true',
                      help='Include diff/patch content in output (makes output much larger)')
    parser.add_argument('--limit', type=int,
                      help='Limit number of PRs to analyze (useful for large result sets)')
    parser.add_argument('--get-draft', action='store_true',
                      help='Include draft PRs in analysis (default: exclude drafts)')
    parser.add_argument('--all-prs', action='store_true',
                      help='Include all PRs regardless of merge status (default: merged only)')
    
    args = parser.parse_args()
    
    # Get token from args or environment
    token = args.token or os.getenv('GITHUB_TOKEN')
    
    # Initialize analyzer
    analyzer = GitHubPRFileAnalyzer(token=token)
    
    # Analyze repository
    results = analyzer.analyze_pr_file_changes(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        author=args.author,
        start_date=args.start_date,
        state=args.state,
        include_patch=args.include_patch,
        limit=args.limit,
        merged_only=not args.all_prs,
        include_draft=args.get_draft
    )
    
    if results:
        # Print summary
        analyzer.print_summary(results)
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n{'=' * 70}")
            print(f"✅ Detailed results saved to: {args.output}")
    else:
        print("Analysis failed or returned no results.")
        sys.exit(1)


if __name__ == "__main__":
    main()
