"""
Primary Engine Automation Coordinator.
"""
import asyncio
import logging
import time
from typing import Dict, Any

from config.settings import CONFIG
from core.risk_manager import RiskManager
from core.market_data import MarketDataOrchestrator
from core.execution import LiveExecutionEngine
from core.state_manager import RedisStateManager
from core.unwinding import UnwindingEngine
from utils.notifications import TelemetryNotifier

logger = logging.getLogger("CrossProtocolArbEngine")

class ArbitrageBot:
    """Controls the long-running operational lifecycle and loop logic of the enterprise system."""
    def __init__(self):
        self.risk_manager = RiskManager(CONFIG)
        self.state_db = RedisStateManager(CONFIG)
        self.data_feed = MarketDataOrchestrator(CONFIG["TARGET_TOKENS"])
        self.notifier = TelemetryNotifier(CONFIG)
        self.executor = LiveExecutionEngine(
            CONFIG["WEB3_RPC_URL"], CONFIG["WALLET_PRIVATE_KEY"], 
            CONFIG["CASINO_ROUTER_ADDRESS"], CONFIG["CASINO_ABI"]
        )
        self.unwinder = UnwindingEngine(CONFIG, self.risk_manager, self.executor, self.state_db)
        self.active_positions: Dict[str, Dict[str, Any]] = {}

    async def initialize_system(self) -> None:
        """Executes core dependencies start sequences during the bootstrap loop phase."""
        await self.state_db.connect()
        self.active_positions = await self.state_db.fetch_active_positions()
        for token, pos in self.active_positions.items():
            self.risk_manager.update_exposure(token, pos["size_usd"])

    async def evaluate_and_route_token(self, token: str) -> None:
        """Drives processing loops, handles evaluation, validation, and near-atomic execution pipelines."""
        try:
            hl_task = self.data_feed.get_hyperliquid_metrics(token)
            uni_task = self.data_feed.get_uniswap_v3_price(token)
            casino_task = self.data_feed.get_casino_native_spot_price(token)

            hl_data, uni_price, casino_spot_price = await asyncio.gather(hl_task, uni_task, casino_task)
            funding_apr = hl_data["funding_rate_apr"]
            perp_price = hl_data["perp_price"]

            market_state_snapshot = {
                token: {"funding_rate_apr": funding_apr, "perp_price": perp_price, "casino_spot_price": casino_spot_price}
            }
            await self.unwinder.monitor_and_unwind_positions(self.active_positions, market_state_snapshot)

            # Evaluate Entry Conditions
            if token not in self.active_positions and funding_apr <= CONFIG["FUNDING_THRESHOLD_APR"]:
                logger.info(f"[ARBITRAGE WINDOW OPENED] Alpha detected for {token} at {funding_apr*100:.2f}% APR.")
                
                target_allocation_usd = 10000.0
                if not self.risk_manager.validate_execution_safety(token, target_allocation_usd, casino_spot_price, perp_price):
                    return

                # Leg A Entry: Buy Spot Asset inside the native speculative Casino app contract environment
                spot_success = await self.executor.execute_casino_spot_buy(
                    token_address="0x0000000000000000000000000000000000000000", 
                    amount_in_wei=int((target_allocation_usd / casino_spot_price) * 10**18), min_amount_out=0
                )
                
                if spot_success:
                    # Leg B Entry: Short identical delta mapping units inside Hyperliquid perpetual futures engine
                    perp_tokens = target_allocation_usd / perp_price
                    perp_success = await self.executor.execute_hyperliquid_perp_short(token, is_buy=False, sz=perp_tokens, px=perp_price)
                    
                    if perp_success:
                        self.risk_manager.update_exposure(token, target_allocation_usd)
                        position_payload = {
                            "token_address": "0x0000000000000000000000000000000000000000",
                            "size_usd": target_allocation_usd, "entry_price": casino_spot_price
                        }
                        self.active_positions[token] = position_payload
                        await self.state_db.record_position_entry(token, target_allocation_usd, position_payload["token_address"], casino_spot_price)
                        
                        # Disptach clean rich mobile metadata notification feeds
                        await self.notifier.send_trade_alert(token, "Entry Opened", target_allocation_usd, casino_spot_price, funding_apr)
                        logger.info(f"🚀 [ARBITRAGE ENTRY SUCCESS] Delta-neutral spread completely secured for {token}.")
                    else:
                        reason = f"Execution unbalance: Spot leg filled for {token} but matching Hyperliquid Perp short failed to clear."
                        self.risk_manager.trigger_global_circuit_breaker(reason)
                        await self.notifier.send_critical_risk_alert(reason)

        except Exception as e:
            logger.error(f"[SYSTEM INTERNAL ERROR] Core run failure on processing asset ticker {token}: {str(e)}")

    async def run_forever(self) -> None:
        """Heartbeat control layer maintaining deterministic iteration velocity."""
        await self.initialize_system()
        logger.info("Starting Cross-Protocol Yield Harvester Engine Operations Layer...")
        while not self.risk_manager.circuit_breaker_tripped:
            start_time = time.time()
            tasks = [self.evaluate_and_route_token(token) for token in CONFIG["TARGET_TOKENS"]]
            await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            sleep_duration = max(0.1, CONFIG["POLLING_INTERVAL_SECONDS"] - elapsed)
            await asyncio.sleep(sleep_duration)
