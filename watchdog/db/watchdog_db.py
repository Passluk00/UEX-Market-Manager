from typing import Optional
import asyncpg
from asyncpg.pool import Pool
from contextlib import asynccontextmanager
import logging
from config import *

class DatabasePool:
    """Gestisce il pool di connessioni PostgreSQL"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        
    async def create_pool(self) -> Pool:
        """Crea il pool di connessioni"""
        try:
            self.pool = await asyncpg.create_pool(**DB_CONFIG)
            logging.info("Database pool created successfully")
            return self.pool
        except Exception as e:
            logging.error(f"Failed to create database pool: {e}")
            raise
            
    async def close_pool(self):
        """Chiude il pool di connessioni"""
        if self.pool:
            await self.pool.close()
            logging.info("Database pool closed")
            
    @asynccontextmanager
    async def acquire(self):
        """Context manager per acquisire una connessione dal pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            yield connection
            
    async def execute(self, query: str, *args):
        """Esegue una query senza ritornare risultati"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
            
    async def fetch(self, query: str, *args):
        """Esegue una query e ritorna tutti i risultati"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
            
    async def fetchrow(self, query: str, *args):
        """Esegue una query e ritorna una singola riga"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

# Istanza globale
db_pool = DatabasePool()
