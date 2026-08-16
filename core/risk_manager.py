"""
Institutional-Grade Real-Time Risk Guardrails.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("CrossProtocolArbEngine")

class RiskManager:
    """Manages system thresholds, capital bounds, and global safety triggers."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_exposure_usd: Dict[str, float] = {t: 0.0 for t in config["TARGET_TOKENS"]}
        self.circuit_breaker_tripped = False

    def validate_execution_safety(self, token: str, size_usd: float, spot_price: float, perp_price: float) -> bool:
        """Validates all core exposure and pricing constraints prior to trade execution."""
        if self.circuit_breaker_tripped:
            logger.critical(f"[RISK REJECT] Circuit breaker active. Blocking execution for {token}.")
            return False

        # 1. Position Sizing Validation
        if self.active_exposure_usd.get(token, 0.0) + size_usd > self.config["MAX_POSITION_SIZE_USD"]:
            logger.warning(f"[RISK REJECT] Allocation limit exceeded for {token}. Cap: ${self.config['MAX_POSITION_SIZE_USD']}")
            return False

        # 2. Input Sanity Checks
        if spot_price <= 0 or perp_price <= 0:
            logger.error(f"[RISK REJECT] Invalid price inputs detected for {token}. Spot: {spot_price}, Perp: {perp_price}")
            return False

        # 3. Dislocation & Slippage Deviation Boundary Check
        price_deviation_bps = abs((perp_price - spot_price) / spot_price) * 10000
        if price_deviation_bps > self.config["MAX_SLIPPAGE_BPS"]:
            logger.warning(f"[RISK REJECT] Price deviation outside parameters: {price_deviation_bps:.2f} bps. Max: {self.config['MAX_SLIPPAGE_BPS']} bps")
            return False

        return True

    def update_exposure(self, token: str, size_usd: float) -> None:
        """Dynamically tracks absolute exposure limits for downstream orchestration layers."""
        if token not in self.active_exposure_usd:
            self.active_exposure_usd[token] = 0.0
        self.active_exposure_usd[token] += size_usd
        logger.info(f"[RISK EXPOSURE UPDATE] {token} exposure is now: ${self.active_exposure_usd[token]:,.2f}")

    def trigger_global_circuit_breaker(self, reason: str) -> None:
        """Instantly disables the execution routine when state mismatches occur."""
        self.circuit_breaker_tripped = True
        logger.critical(f"🚨 [CIRCUIT BREAKER ACTIVATED] Operational systems frozen. Reason: {reason}")
