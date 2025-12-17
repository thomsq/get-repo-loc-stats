#!/usr/bin/env python3
"""
GitHub Repository Pull Requests Retrieval Tool

This script retrieves all Pull Requests for a specific repository and username
starting from a specified date (default: 2025-01-01).
It fetches PR numbers, titles, states, and basic statistics.

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


class GitHubPRAnalyzer:
    """GitHub repository Pull Request analyzer"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub PR analyzer
        
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
    
    def get_pull_requests(self, repo_owner: str, repo_name: str, author: str, since_date: str, state: str = "all") -> List[Dict]:
        """
        Get pull requests by a specific author since the given date
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to filter PRs
            since_date: ISO format date string (e.g., '2025-01-01T00:00:00Z')
            state: PR state filter ('open', 'closed', 'all')
            
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
                        filtered_prs.append(pr)
                    else:
                        # Since PRs are sorted by creation date (desc), we can stop here
                        return pull_requests
            
            pull_requests.extend(filtered_prs)
            page += 1
            
            # GitHub API pagination limit check
            if len(page_prs) < per_page:
                break
        
        print(f"Found {len(pull_requests)} PRs by {author} since {since_date}")
        return pull_requests
    
    def get_pr_details(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict:
        """
        Get detailed information for a specific pull request
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            pr_number: Pull request number
            
        Returns:
            Dictionary containing PR details
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
        
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"Warning: Could not fetch details for PR #{pr_number}: {response.status_code}")
            return {}
        
        return response.json()
    
    def analyze_repo_prs(self, repo_owner: str, repo_name: str, author: str, start_date: str = "2025-01-01", state: str = "all") -> Dict:
        """
        Analyze Pull Requests for a repository
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to analyze
            start_date: Start date in YYYY-MM-DD format
            state: PR state filter ('open', 'closed', 'all')
            
        Returns:
            Dictionary containing PR statistics
        """
        # Convert start_date to ISO format
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            since_date = start_datetime.isoformat()
        except ValueError:
            print(f"Error: Invalid date format '{start_date}'. Please use YYYY-MM-DD format.")
            return {}
        
        print(f"\nAnalyzing Pull Requests for repository: {repo_owner}/{repo_name}")
        print(f"Author: {author}")
        print(f"Start date: {start_date}")
        print(f"State filter: {state}")
        print("-" * 50)
        
        # Get pull requests
        prs = self.get_pull_requests(repo_owner, repo_name, author, since_date, state)
        
        if not prs:
            return {
                'repository': f"{repo_owner}/{repo_name}",
                'author': author,
                'start_date': start_date,
                'state_filter': state,
                'total_prs': 0,
                'open_prs': 0,
                'closed_prs': 0,
                'merged_prs': 0,
                'draft_prs': 0,
                'pull_requests': []
            }
        
        pr_details = []
        open_count = 0
        closed_count = 0
        merged_count = 0
        draft_count = 0
        
        print(f"\nProcessing {len(prs)} pull requests...")
        
        for i, pr in enumerate(prs, 1):
            print(f"Processing PR {i}/{len(prs)}: #{pr['number']}...")
            
            # Count PR states
            if pr['state'] == 'open':
                open_count += 1
            elif pr['state'] == 'closed':
                closed_count += 1
                if pr.get('merged_at'):
                    merged_count += 1
            
            if pr.get('draft', False):
                draft_count += 1
            
            # Extract PR information
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
                'additions': pr.get('additions', 0),
                'deletions': pr.get('deletions', 0),
                'changed_files': pr.get('changed_files', 0),
                'commits': pr.get('commits', 0),
                'comments': pr.get('comments', 0),
                'review_comments': pr.get('review_comments', 0),
                'labels': [label['name'] for label in pr.get('labels', [])],
                'base_branch': pr['base']['ref'],
                'head_branch': pr['head']['ref']
            }
            
            pr_details.append(pr_info)
        
        # Sort PRs by number (descending)
        pr_details.sort(key=lambda x: x['number'], reverse=True)
        
        results = {
            'repository': f"{repo_owner}/{repo_name}",
            'author': author,
            'start_date': start_date,
            'state_filter': state,
            'total_prs': len(prs),
            'open_prs': open_count,
            'closed_prs': closed_count,
            'merged_prs': merged_count,
            'draft_prs': draft_count,
            'pull_requests': pr_details
        }
        
        return results
    
    def print_summary(self, results: Dict):
        """Print a formatted summary of the results"""
        if not results:
            print("No results to display.")
            return
        
        print("\n" + "=" * 60)
        print("PULL REQUESTS ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Repository: {results['repository']}")
        print(f"Author: {results['author']}")
        print(f"Analysis period: From {results['start_date']} to present")
        print(f"State filter: {results['state_filter']}")
        print("-" * 60)
        print(f"Total PRs: {results['total_prs']}")
        print(f"Open PRs: {results['open_prs']}")
        print(f"Closed PRs: {results['closed_prs']}")
        print(f"Merged PRs: {results['merged_prs']}")
        print(f"Draft PRs: {results['draft_prs']}")
        print("-" * 60)
        
        if results['total_prs'] > 0:
            merge_rate = (results['merged_prs'] / results['total_prs']) * 100
            print(f"Merge rate: {merge_rate:.1f}%")
        
        print(f"\nPR Numbers (most recent first):")
        pr_numbers = [str(pr['number']) for pr in results['pull_requests']]
        
        # Print PR numbers in chunks of 10 for readability
        for i in range(0, len(pr_numbers), 10):
            chunk = pr_numbers[i:i+10]
            print(f"  {', '.join(chunk)}")
        
        print(f"\nRecent PRs Details:")
        for i, pr in enumerate(results['pull_requests'][:10], 1):
            status_emoji = "🟢" if pr['state'] == 'open' else "🔴" if pr['state'] == 'closed' else "⚪"
            merged_text = " (merged)" if pr['merged_at'] else ""
            draft_text = " [DRAFT]" if pr['draft'] else ""
            print(f"{i:2d}. {status_emoji} #{pr['number']}{draft_text} - {pr['title'][:50]}...{merged_text}")


def main():
    """Main function to run the PR analyzer"""
    parser = argparse.ArgumentParser(
        description='Analyze GitHub repository Pull Requests',
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
    
    args = parser.parse_args()
    
    # Get token from args or environment
    token = args.token or os.getenv('GITHUB_TOKEN')
    
    # Initialize analyzer
    analyzer = GitHubPRAnalyzer(token=token)
    
    # Analyze repository
    results = analyzer.analyze_repo_prs(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        author=args.author,
        start_date=args.start_date,
        state=args.state
    )
    
    if results:
        # Print summary
        analyzer.print_summary(results)
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nDetailed results saved to: {args.output}")
    else:
        print("Analysis failed or returned no results.")
        sys.exit(1)


if __name__ == "__main__":
    main()