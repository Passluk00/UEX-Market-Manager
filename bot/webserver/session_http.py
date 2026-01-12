import aiohttp

_http_session: aiohttp.ClientSession | None = None

async def init_http():
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()

def get_http_session() -> aiohttp.ClientSession:
    if _http_session is None:
        raise RuntimeError("HTTP session not initialized")
    return _http_session

async def close_http():
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()
