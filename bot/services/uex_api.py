# services/uex_api.py
import aiohttp
import logging
from db import  save_user_session
from directory import API_GET_USER,API_POST_MESSAGE


"""
Fetches the official UEX username via API and updates the user's session in the database.

This function validates the provided credentials (bearer token and secret key) 
against the UEX API. If successful, it retrieves the canonical username and 
persists it to the database to ensure future messages are correctly attributed.

Args:
    user_id (str): The unique Discord user ID.
    secret_key (str): The UEX API secret key provided by the user.
    bearer_token (str): The UEX API bearer token provided by the user.
    username_guess (str): The username input by the user for validation.
    session (aiohttp.ClientSession): The active asynchronous HTTP session.

Returns:
    str | None: The confirmed UEX username if successful, or None if the 
                API call fails or credentials are invalid.
"""
async def fetch_and_store_uex_username(user_id: str, secret_key: str, bearer_token: str, username_guess: str, session: "aiohttp.ClientSession") -> str | None:
    """
    Retrieve the UEX username via API using the past session.
    """
    try:
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "secret-key": secret_key,
            "Content-Type": "application/json"
        }
        async with session.get(f"{API_GET_USER}?username={username_guess}", headers=headers) as resp:
            if resp.status != 200:
                logging.warning(f"Error fetch UEX username for {user_id}: {resp.status}")
                return None
            data = await resp.json()
            uex_username = data.get("data", {}).get("username")
            if not uex_username:
                return None

        await save_user_session(
            user_id=user_id,
            uex_username=uex_username
        )

        return uex_username

    except Exception as e:
        logging.exception(f"Errore fetch_and_store_uex_username per {user_id}: {e}")
        return None



"""
Sends a message to an ongoing UEX negotiation via the UEX API.

This function bridges Discord message replies to the UEX platform. It sends 
a POST request with the negotiation hash and the message content, using the 
user's specific authentication headers.

Args:
    session (aiohttp.ClientSession): The shared asynchronous HTTP session.
    bearer_token (str): The user's UEX bearer token.
    secret_key (str): The user's UEX secret key.
    notif_hash (str): The unique hash identifier for the specific negotiation.
    message (str): The text content to be sent to the negotiation partner.
    is_production (int): Flag to toggle between production (1) and test (0) environments.

Returns:
    tuple[bool, str]: A tuple containing a success boolean and an error message 
                      (which is empty if the operation was successful).
"""
async def send_uex_message(
    *,
    session: aiohttp.ClientSession,
    bearer_token: str,
    secret_key: str,
    notif_hash: str,
    message: str,
    is_production: int = 1
) -> tuple[bool, str]:
    """
    Send a message to a UEX negotiation.

    Args:
        session (aiohttp.ClientSession): Shared HTTP session
        bearer_token (str): UEX bearer token
        secret_key (str): UEX secret key
        notif_hash (str): Negotiation hash
        message (str): Message text
        is_production (int): 1 production, 0 test

    Returns:
        tuple[bool, str]:
        - True, "" if successful
        - False, error message if unsuccessful
    """

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "secret-key": secret_key,
        "Content-Type": "application/json"
    }

    payload = {
        "is_production": is_production,
        "hash": notif_hash,
        "message": message
    }

    logging.info(f"📤 UEX SEND | hash={notif_hash}")

    try:
        async with session.post(API_POST_MESSAGE, headers=headers, json=payload) as resp:
            if resp.status == 200:
                return True, ""

            text = await resp.text()
            logging.warning(f"⚠️ UEX ERROR {resp.status}: {text}")
            return False, f"{resp.status}: {text[:200]}"

    except Exception as e:
        logging.exception("💥 UEX connection error")
        return False, str(e)
