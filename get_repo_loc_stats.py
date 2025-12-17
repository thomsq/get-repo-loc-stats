#!/usr/bin/env python3
"""
GitHub Repository LOC (Lines of Code) Statistics Tool

This script retrieves Lines of Code statistics for a specific repository and username
starting from a specified date (default: 2025-01-01).
It calculates the total changes (additions + deletions) for commits by the specified author.
"""

import requests
import json
from datetime import datetime, timezone
import argparse
import sys
from typing import Dict, List, Optional, Tuple


class GitHubLOCAnalyzer:
    """GitHub repository LOC analyzer"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the GitHub LOC analyzer
        
        Args:
            token: GitHub personal access token (optional but recommended for higher rate limits)
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })
    
    def get_commits(self, repo_owner: str, repo_name: str, author: str, since_date: str) -> List[Dict]:
        """
        Get commits by a specific author since the given date
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to filter commits
            since_date: ISO format date string (e.g., '2025-01-01T00:00:00Z')
            
        Returns:
            List of commit objects
        """
        commits = []
        page = 1
        per_page = 100
        
        while True:
            url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits"
            params = {
                'author': author,
                'since': since_date,
                'per_page': per_page,
                'page': page
            }
            
            print(f"Fetching commits page {page}...")
            response = self.session.get(url, params=params)
            
            if response.status_code == 404:
                print(f"Error: Repository {repo_owner}/{repo_name} not found or not accessible")
                return []
            elif response.status_code == 403:
                print("Error: API rate limit exceeded or access forbidden")
                return []
            elif response.status_code != 200:
                print(f"Error fetching commits: {response.status_code} - {response.text}")
                return []
            
            page_commits = response.json()
            if not page_commits:
                break
                
            commits.extend(page_commits)
            page += 1
            
            # GitHub API pagination limit check
            if len(page_commits) < per_page:
                break
        
        print(f"Found {len(commits)} commits by {author} since {since_date}")
        return commits
    
    def get_commit_stats(self, repo_owner: str, repo_name: str, commit_sha: str) -> Tuple[int, int]:
        """
        Get additions and deletions for a specific commit
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            commit_sha: Commit SHA hash
            
        Returns:
            Tuple of (additions, deletions)
        """
        url = f"{self.base_url}/repos/{repo_owner}/{repo_name}/commits/{commit_sha}"
        
        response = self.session.get(url)
        
        if response.status_code != 200:
            print(f"Warning: Could not fetch stats for commit {commit_sha}: {response.status_code}")
            return 0, 0
        
        commit_data = response.json()
        stats = commit_data.get('stats', {})
        
        additions = stats.get('additions', 0)
        deletions = stats.get('deletions', 0)
        
        return additions, deletions
    
    def analyze_repo_loc(self, repo_owner: str, repo_name: str, author: str, start_date: str = "2025-01-01") -> Dict:
        """
        Analyze LOC statistics for a repository
        
        Args:
            repo_owner: Repository owner username
            repo_name: Repository name
            author: Author username to analyze
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing LOC statistics
        """
        # Convert start_date to ISO format
        try:
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
            since_date = start_datetime.isoformat()
        except ValueError:
            print(f"Error: Invalid date format '{start_date}'. Please use YYYY-MM-DD format.")
            return {}
        
        print(f"\nAnalyzing LOC for repository: {repo_owner}/{repo_name}")
        print(f"Author: {author}")
        print(f"Start date: {start_date}")
        print("-" * 50)
        
        # Get commits
        commits = self.get_commits(repo_owner, repo_name, author, since_date)
        
        if not commits:
            return {
                'repository': f"{repo_owner}/{repo_name}",
                'author': author,
                'start_date': start_date,
                'total_commits': 0,
                'total_additions': 0,
                'total_deletions': 0,
                'total_changes': 0,
                'commits': []
            }
        
        total_additions = 0
        total_deletions = 0
        commit_details = []
        
        print(f"\nFetching detailed statistics for {len(commits)} commits...")
        
        for i, commit in enumerate(commits, 1):
            commit_sha = commit['sha']
            commit_message = commit['commit']['message'].split('\n')[0]  # First line only
            commit_date = commit['commit']['author']['date']
            
            print(f"Processing commit {i}/{len(commits)}: {commit_sha[:8]}...")
            
            additions, deletions = self.get_commit_stats(repo_owner, repo_name, commit_sha)
            
            total_additions += additions
            total_deletions += deletions
            
            commit_details.append({
                'sha': commit_sha,
                'message': commit_message,
                'date': commit_date,
                'additions': additions,
                'deletions': deletions,
                'total_changes': additions + deletions
            })
        
        total_changes = total_additions + total_deletions
        
        results = {
            'repository': f"{repo_owner}/{repo_name}",
            'author': author,
            'start_date': start_date,
            'total_commits': len(commits),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_changes': total_changes,
            'commits': commit_details
        }
        
        return results
    
    def print_summary(self, results: Dict):
        """Print a formatted summary of the results"""
        if not results:
            print("No results to display.")
            return
        
        print("\n" + "=" * 60)
        print("LOC ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Repository: {results['repository']}")
        print(f"Author: {results['author']}")
        print(f"Analysis period: From {results['start_date']} to present")
        print(f"Total commits: {results['total_commits']}")
        print("-" * 60)
        print(f"Total additions: {results['total_additions']:,} lines")
        print(f"Total deletions: {results['total_deletions']:,} lines")
        print(f"Total changes: {results['total_changes']:,} lines")
        print("-" * 60)
        
        if results['total_commits'] > 0:
            avg_changes = results['total_changes'] / results['total_commits']
            print(f"Average changes per commit: {avg_changes:.1f} lines")
        
        print("\nTop 10 commits by changes:")
        sorted_commits = sorted(results['commits'], key=lambda x: x['total_changes'], reverse=True)
        
        for i, commit in enumerate(sorted_commits[:10], 1):
            print(f"{i:2d}. {commit['sha'][:8]} ({commit['total_changes']:4d} changes) - {commit['message'][:50]}...")


def main():
    """Main function to run the LOC analyzer"""
    parser = argparse.ArgumentParser(description='Analyze GitHub repository LOC statistics')
    parser.add_argument('repo_owner', help='Repository owner username')
    parser.add_argument('repo_name', help='Repository name')
    parser.add_argument('author', help='Author username to analyze')
    parser.add_argument('--start-date', default='2025-01-01', 
                      help='Start date in YYYY-MM-DD format (default: 2025-01-01)')
    parser.add_argument('--token', help='GitHub personal access token')
    parser.add_argument('--output', help='Output file path to save results as JSON')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = GitHubLOCAnalyzer(token=args.token)
    
    # Analyze repository
    results = analyzer.analyze_repo_loc(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        author=args.author,
        start_date=args.start_date
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