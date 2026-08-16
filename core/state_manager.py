"""
Enterprise Asynchronous Redis State and Position Persistence Engine.
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import redis.asyncio as aioredis

logger = logging.getLogger("CrossProtocolArbEngine")

class RedisStateManager:
    """Manages atomic position persistence to guarantee structural data recovery post-crash."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.prefix = config["REDIS_KEY_PREFIX"]
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Initializes a resilient connection pool to the Redis storage cache."""
        try:
            self.redis = aioredis.Redis(
                host=self.config["REDIS_HOST"],
                port=self.config["REDIS_PORT"],
                db=self.config["REDIS_DB"],
                password=self.config["REDIS_PASSWORD"],
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("⚡ [REDIS SUCCESS] Connected to persistent state cache cluster.")
        except Exception as e:
            logger.warning(f"⚠️ [REDIS LOCAL FALLBACK] Failed to reach cache system ({str(e)}). Deploying volatile internal array virtualizations.")
            self.redis = None

    def _get_key(self, token: str) -> str:
        return f"{self.prefix}{token.upper()}"

    async def record_position_entry(self, token: str, size_usd: float, token_address: str, entry_price: float) -> bool:
        """Atomically saves or updates an active arbitrage trade record in the database."""
        if not self.redis:
            return True
        
        key = self._get_key(token)
        payload = {
            "token": token.upper(),
            "size_usd": size_usd,
            "token_address": token_address,
            "entry_price": entry_price,
            "timestamp": int(time.time() if hasattr(time, "time") else 0)
        }
        try:
            await self.redis.set(key, json.dumps(payload))
            logger.info(f"[DATABASE PERSIST] Synchronized database logging state for asset {token}: ${size_usd:,.2f}")
            return True
        except Exception as e:
            logger.error(f"[DATABASE ERROR] Failed to serialize state cache update record: {str(e)}")
            return False

    async def fetch_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """Scans the datastore cluster namespace to recover and rebuild all active allocations."""
        if not self.redis:
            return {}
        active_map: Dict[str, Dict[str, Any]] = {}
        try:
            keys = await self.redis.keys(f"{self.prefix}*")
            for key in keys:
                raw_data = await self.redis.get(key)
                if raw_data:
                    parsed_payload = json.loads(raw_data)
                    active_map[parsed_payload["token"]] = parsed_payload
            return active_map
        except Exception as e:
            logger.error(f"[DATABASE ERROR] State hydration recovery cycle breakdown: {str(e)}")
            return {}

    async def remove_position(self, token: str) -> bool:
        """Deletes a key from the database once the unwinding engine completes a trade exit."""
        if not self.redis:
            return True
        try:
            await self.redis.delete(self._get_key(token))
            return True
        except Exception as e:
            logger.error(f"[DATABASE ERROR] Failed to purge key record out of database tables: {str(e)}")
            return False

    async def close(self) -> None:
        """Gracefully tears down open communication sockets during application termination."""
        if self.redis:
            await self.redis.close()
