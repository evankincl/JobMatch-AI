"""Scheduled job discovery. Uses only public job feeds and Supabase secrets."""
import sys
from core import discover, save_jobs

if __name__=='__main__':
    jobs, errors = discover()
    print(f'Filtered matching jobs: {len(jobs)}')
    for error in errors: print(f'Feed warning: {error}',file=sys.stderr)
    if errors and not jobs:
        raise SystemExit('No jobs found and at least one feed failed; inspect board slugs and API availability.')
    print(f'Saved {save_jobs(jobs)} jobs')
