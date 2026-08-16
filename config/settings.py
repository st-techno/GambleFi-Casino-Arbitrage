"""
Enterprise Configuration Subsystem.
"""
import os
from typing import Dict, Any

CONFIG: Dict[str, Any] = {
    # Strategy Rules & Parameter Arrays
    "TARGET_TOKENS": ["RLB", "SHFL"],
    "FUNDING_THRESHOLD_APR": -2.00,       # -200% APR (Retail short-squeeze trigger boundary)
    "MAX_SLIPPAGE_BPS": 50,               # 0.50% maximum slippage allocation safety buffer
    "MAX_POSITION_SIZE_USD": 50000.0,     # Maximum absolute exposure cap per asset target
    "MIN_PROFIT_SPREAD_BPS": 75,          # Structural minimum target edge net of exchange fees
    "LEVERAGE": 1,                        # 1x directional short hedge deployment parameters
    "POLLING_INTERVAL_SECONDS": 2,         # Core engine automation heartbeat cadence ticker
    
    # Live Node Connections & Key Infrastructures
    "WEB3_RPC_URL": os.getenv("WEB3_RPC_URL", "https://alchemy.com"),
    "HYPERLIQUID_API_URL": "https://hyperliquid.xyz",
    "WALLET_PRIVATE_KEY": os.getenv("WALLET_PRIVATE_KEY", "0x0000000000000000000000000000000000000000000000000000000000000000"),
    
    # Targeted Platform Protocol Context Specifications
    "CASINO_ROUTER_ADDRESS": "0x1111111254fb6c44bac0bed2854e76f90643097d", # Router contract address placeholder
    "CASINO_ABI": [
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"}
            ],
            "name": "swapExactETHForTokens",
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
            "stateMutability": "payable",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "WETH",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ],
    
    # Asynchronous Redis Persistence Core Layer Credentials
    "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
    "REDIS_PORT": int(os.getenv("REDIS_PORT", 6379)),
    "REDIS_DB": int(os.getenv("REDIS_DB", 0)),
    "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD", None),
    "REDIS_KEY_PREFIX": "arb_bot:positions:",
    
    # Mobile Telemetry Notification Settings
    "ENABLE_NOTIFICATIONS": True,
    "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com"),
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "your_token"),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "your_chat_id")
}
