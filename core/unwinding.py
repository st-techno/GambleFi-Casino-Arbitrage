"""
Institutional-Grade Position Unwinding and Profit-Realization Engine.
"""
import logging
from typing import Dict, Any
from core.risk_manager import RiskManager
from core.execution import LiveExecutionEngine
from core.state_manager import RedisStateManager

logger = logging.getLogger("CrossProtocolArbEngine")

class UnwindingEngine:
    """Monitors active delta-neutral positions and systematically unwinds them when spreads normalize."""
    def __init__(self, config: Dict[str, Any], risk_manager: RiskManager, executor: LiveExecutionEngine, state_db: RedisStateManager):
        self.config = config
        self.risk_manager = risk_manager
        self.executor = executor
        self.state_db = state_db
        self.exit_threshold_apr = -0.15 # Exit target set to -15% APR

    async def monitor_and_unwind_positions(self, active_positions: Dict[str, Dict[str, Any]], current_market_data: Dict[str, Any]) -> None:
        """Evaluates live funding metrics against open exposure database layers to trigger automated exits."""
        for token, position_details in list(active_positions.items()):
            size_usd = position_details.get("size_usd", 0.0)
            if size_usd <= 0 or token not in current_market_data:
                continue

            current_funding_apr = current_market_data[token]["funding_rate_apr"]
            perp_price = current_market_data[token]["perp_price"]
            casino_spot_price = current_market_data[token]["casino_spot_price"]

            if current_funding_apr > self.exit_threshold_apr:
                logger.info(f"⚠️ [EXIT TRIGGER ACTIVE] {token} funding normalized above target exit bands: {current_funding_apr*100:.2f}% APR.")
                
                # Leg B Execution: Buy to close the Perp Short position first (Liquid venue)
                perp_tokens_to_buy = size_usd / perp_price
                perp_exit_success = await self.executor.execute_hyperliquid_perp_short(
                    asset_ticker=token, is_buy=True, sz=perp_tokens_to_buy, px=perp_price * 1.005
                )

                if perp_exit_success:
                    # Leg A Execution: Liquidation step of spot layers inside casino contracts
                    approx_tokens_to_sell = (size_usd / casino_spot_price) * 10**18
                    spot_exit_success = await self.executor.execute_casino_spot_buy(
                        token_address=position_details.get("token_address", "0x0"),
                        amount_in_wei=int(approx_tokens_to_sell), min_amount_out=0
                    )

                    if spot_exit_success:
                        logger.info(f"🎉 [UNWIND EXECUTION COMPLETE] Cleared positions successfully for {token}.")
                        self.risk_manager.update_exposure(token, -size_usd)
                        await self.state_db.remove_position(token)
                        active_positions.pop(token, None)
                    else:
                        self.risk_manager.trigger_global_circuit_breaker(
                            f"CRITICAL: Closed perp short hedge but failed to sell spot asset for {token}. Position is naked long!"
                        )
