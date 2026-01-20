import db.pool
import logging



async def save_negotiation_link(hash, buyer, seller):
    
    """
    Saves or updates a negotiation link in the database.

    Args:
        hash (str): The unique negotiation hash identifier.
        buyer (str): The username or ID of the buyer.
        seller (str): The username or ID of the seller.

    Returns:
        None
    """    
    
    async with db.pool.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO negotiation_links (negotiation_hash, buyer_id, seller_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (negotiation_hash)
            DO UPDATE SET
                buyer_id = EXCLUDED.buyer_id,
                seller_id = EXCLUDED.seller_id
        """, hash, buyer, seller)
    logging.info(f"🔗 Link Saved: {hash} → buyer={buyer}, seller={seller}")


async def get_negotiation_link(hash):
    
    """
    Retrieves the buyer and seller details associated with a specific negotiation hash.

    Args:
        hash (str): The unique negotiation hash identifier.

    Returns:
        dict|None: A dictionary with 'buyer_id' and 'seller_id' if found, otherwise None.
    """
    
    async with db.pool.db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT buyer_id, seller_id FROM negotiation_links WHERE negotiation_hash=$1",
            hash
        )
        return {"buyer_id": row["buyer_id"], "seller_id": row["seller_id"]} if row else None


async def delete_negotiation_link(hash):
    
    """
    Removes a negotiation link from the database using its hash.

    Args:
        hash (str): The unique negotiation hash identifier to be deleted.

    Returns:
        None
    """
    
    async with db.pool.db_pool.acquire() as conn:
        await conn.execute("DELETE FROM negotiation_links WHERE negotiation_hash=$1", hash)
    logging.info(f"❌ Link Deleted: {hash}")
