import os
import logging
import aiohttp
from typing import Optional
import config
from config import GITHUB_REPO, GITHUB_BRANCH, COMMIT_SHA_FILE

# Esponiamo la variabile GITHUB_TOKEN nel modulo così i test possono patcharla
GITHUB_TOKEN = getattr(config, "GITHUB_TOKEN", None)

def _auth_headers() -> dict:
    """Returns Authorization header if a GitHub token is configured."""
    # Usa sempre la variabile globale del modulo, così patch funziona
    if GITHUB_TOKEN:
        return {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    return {}

async def get_latest_commit_sha() -> Optional[str]:
    """Ottiene l'ultimo commit SHA dal branch GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{GITHUB_BRANCH}"

    try:
        async with aiohttp.ClientSession(headers=_auth_headers()) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    sha = data['sha']
                    logging.info(f"Latest commit SHA: {sha[:8]}")
                    return sha
                else:
                    logging.error(f"GitHub API error: {response.status} — {await response.text()}")
                    return None
    except Exception as e:
        logging.error(f"Failed to fetch latest commit: {e}")
        return None


async def get_current_commit_sha() -> Optional[str]:
    """
    Legge il commit SHA corrente dal file locale salvato dopo ogni update.

    Il file viene scritto in GIT_REPO_PATH/bot/.git_commit_sha (configurabile
    in config.py tramite COMMIT_SHA_FILE).
    """
    
    try:
        if os.path.exists(COMMIT_SHA_FILE):
            with open(COMMIT_SHA_FILE, 'r') as f:
                sha = f.read().strip()
            if sha:
                logging.info(f"Current commit SHA: {sha[:8]}")
                return sha
        logging.warning(f"No local commit SHA file found at '{COMMIT_SHA_FILE}'")
        return None
    except Exception as e:
        logging.error(f"Failed to read current commit SHA: {e}")
        return None


async def save_commit_sha(sha: str):
    """Salva il commit SHA corrente nel file locale."""

    try:
        with open(COMMIT_SHA_FILE, 'w') as f:
            f.write(sha)
        logging.info(f"Saved commit SHA: {sha[:8]}")
    except Exception as e:
        logging.error(f"Failed to save commit SHA: {e}")


async def get_commit_info(sha: str) -> Optional[dict]:
    """
    Ottiene informazioni dettagliate su un commit specifico.

    Returns:
        dict con sha, message, author, date — oppure None in caso di errore.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/{sha}"

    try:
        async with aiohttp.ClientSession(headers=_auth_headers()) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'sha': data['sha'],
                        'message': data['commit']['message'],
                        'author': data['commit']['author']['name'],
                        'date': data['commit']['author']['date']
                    }
                else:
                    logging.error(f"GitHub API error: {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Failed to fetch commit info: {e}")
        return None