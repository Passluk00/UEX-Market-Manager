import logging
import aiohttp
import os
from typing import Optional
from config import GITHUB_REPO, GITHUB_BRANCH

async def get_latest_commit_sha() -> Optional[str]:
    """Ottiene l'ultimo commit SHA dal branch GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    sha = data['sha']
                    logging.info(f"Latest commit SHA: {sha[:8]}")
                    return sha
                else:
                    logging.error(f"GitHub API error: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Failed to fetch latest commit: {e}")
        return None

async def get_current_commit_sha() -> Optional[str]:
    """Legge il commit SHA corrente dal file locale"""
    sha_file = '/app/.git_commit_sha'
    
    try:
        if os.path.exists(sha_file):
            with open(sha_file, 'r') as f:
                sha = f.read().strip()
                logging.info(f"Current commit SHA: {sha[:8]}")
                return sha
        else:
            logging.warning("No local commit SHA file found")
            return None
    except Exception as e:
        logging.error(f"Failed to read current commit SHA: {e}")
        return None

async def save_commit_sha(sha: str):
    """Salva il commit SHA corrente"""
    sha_file = '/app/.git_commit_sha'
    
    try:
        with open(sha_file, 'w') as f:
            f.write(sha)
        logging.info(f"Saved commit SHA: {sha[:8]}")
    except Exception as e:
        logging.error(f"Failed to save commit SHA: {e}")
