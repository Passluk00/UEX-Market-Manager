# bot/tests/test_negotiations.py
"""
Tests per bot/db/negotiations.py

Copre:
- save_negotiation_link() — scrittura, UPSERT
- get_negotiation_link()  — trovato, non trovato
- delete_negotiation_link() — delete eseguito
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_ctx(fetchrow_result=None):
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.execute = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return conn, ctx


class TestSaveNegotiationLink:

    @pytest.mark.asyncio
    async def test_calls_execute_with_hash(self):
        conn, ctx = _make_ctx()

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import save_negotiation_link
            await save_negotiation_link("hash123", "buyer1", "seller1")

        args = conn.execute.call_args[0]
        assert "hash123" in args
        assert "buyer1" in args
        assert "seller1" in args

    @pytest.mark.asyncio
    async def test_uses_upsert_query(self):
        conn, ctx = _make_ctx()

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import save_negotiation_link
            await save_negotiation_link("h", "b", "s")

        query = conn.execute.call_args[0][0]
        assert "ON CONFLICT" in query or "INSERT" in query

    @pytest.mark.asyncio
    async def test_no_exception_on_success(self):
        conn, ctx = _make_ctx()

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import save_negotiation_link
            # Non deve sollevare
            await save_negotiation_link("h", "b", "s")


class TestGetNegotiationLink:

    @pytest.mark.asyncio
    async def test_returns_dict_when_found(self):
        conn, ctx = _make_ctx(fetchrow_result={"buyer_id": "alice", "seller_id": "bob"})

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import get_negotiation_link
            result = await get_negotiation_link("hash123")

        assert result == {"buyer_id": "alice", "seller_id": "bob"}

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        conn, ctx = _make_ctx(fetchrow_result=None)

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import get_negotiation_link
            result = await get_negotiation_link("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_queries_by_hash(self):
        conn, ctx = _make_ctx(fetchrow_result=None)

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import get_negotiation_link
            await get_negotiation_link("specific_hash")

        args = conn.fetchrow.call_args[0]
        assert "specific_hash" in args


class TestDeleteNegotiationLink:

    @pytest.mark.asyncio
    async def test_calls_delete_with_hash(self):
        conn, ctx = _make_ctx()

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import delete_negotiation_link
            await delete_negotiation_link("hash_to_delete")

        args = conn.execute.call_args[0]
        assert "hash_to_delete" in args

    @pytest.mark.asyncio
    async def test_no_exception_when_hash_not_found(self):
        conn, ctx = _make_ctx()

        with patch('db.negotiations.db.pool.db_pool') as mock_pool:
            mock_pool.acquire.return_value = ctx
            from db.negotiations import delete_negotiation_link
            # Non deve sollevare anche se l'hash non esiste
            await delete_negotiation_link("nonexistent_hash")
