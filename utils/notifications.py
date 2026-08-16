"""
Enterprise Async Multi-Channel Telemetry Notification and Monitoring Dispatcher.
"""
import json
import logging
import urllib.request
import urllib.parse
import asyncio
from typing import Dict, Any

logger = logging.getLogger("CrossProtocolArbEngine")

class TelemetryNotifier:
    """Manages secure webhooks to broadcast position changes, PnL updates, and risk warnings."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("ENABLE_NOTIFICATIONS", False)
        self.discord_url = config.get("DISCORD_WEBHOOK_URL")
        self.tg_token = config.get("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = config.get("TELEGRAM_CHAT_ID")

    def _sync_post(self, url: str, data: bytes, headers: dict) -> None:
        """Helper to run blocking network I/O cleanly inside an asynchronous worker pool thread."""
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()

    async def _dispatch_payload(self, url: str, json_data: dict) -> None:
        """Dispatches structured payloads safely using background executor threads."""
        if not self.enabled:
            return
        try:
            payload_bytes = json.dumps(json_data).encode("utf-8")
            headers = {"Content-Type": "application/json", "User-Agent": "ArbBotTelemetry/1.0"}
            await asyncio.to_thread(self._sync_post, url, payload_bytes, headers)
        except Exception as e:
            logger.error(f"[TELEMETRY-ERROR] Failed to dispatch webhook alert to gateway: {str(e)}")

    async def send_trade_alert(self, token: str, side: str, size_usd: float, price: float, rate_apr: float) -> None:
        """Sends clean, structured rich text alerts when trades are opened or closed."""
        emoji = "🟩" if "ENTRY" in side.upper() else "🟪"
        header_text = f"{emoji} **ARB POSITION {side.upper()}**"
        
        discord_embed = {
            "content": None,
            "embeds": [{
                "title": header_text,
                "color": 3066993 if "ENTRY" in side.upper() else 10181046,
                "fields": [
                    {"name": "Asset Target", "value": f"`{token}`", "inline": True},
                    {"name": "Size Allocation", "value": f"${size_usd:,.2f}", "inline": True},
                    {"name": "Trigger Funding", "value": f"{rate_apr*100:.2f}% APR", "inline": True},
                    {"name": "Execution Price Reference", "value": f"${price:.6f}", "inline": False}
                ],
                "footer": {"text": "System Monitor Engine Core Metrics"}
            }]
        }
        
        tg_text = (
            f"{header_text}\n"
            f"• Ticker: {token}\n"
            f"• Vol: ${size_usd:,.2f}\n"
            f"• Yield Vector: {rate_apr*100:.2f}% APR\n"
            f"• Spot Entry Base: ${price:.6f}"
        )
        tg_payload = {"chat_id": self.tg_chat_id, "text": tg_text, "parse_mode": "Markdown"}

        tasks = []
        if self.discord_url and "dummy-url" not in self.discord_url:
            tasks.append(self._dispatch_payload(self.discord_url, discord_embed))
        if self.tg_token and "your_token" not in self.tg_token:
            tg_url = f"https://telegram.org{self.tg_token}/sendMessage"
            tasks.append(self._dispatch_payload(tg_url, tg_payload))
        if tasks:
            await asyncio.gather(*tasks)

    async def send_critical_risk_alert(self, reason: str) -> None:
        """Bypasses standard filtering to alert you instantly if circuit breakers trip."""
        content = f"🚨 **CRITICAL RISK INCIDENT DETECTED**\n```\n{reason}\n```\n@everyone **SYSTEM IS PAUSED**"
        tasks = []
        if self.discord_url and "dummy-url" not in self.discord_url:
            tasks.append(self._dispatch_payload(self.discord_url, {"content": content}))
        if self.tg_token and "your_token" not in self.tg_token:
            tg_url = f"https://telegram.org{self.tg_token}/sendMessage"
            tasks.append(self._dispatch_payload(tg_url, {"chat_id": self.tg_chat_id, "text": content}))
        if tasks:
            await asyncio.gather(*tasks)
