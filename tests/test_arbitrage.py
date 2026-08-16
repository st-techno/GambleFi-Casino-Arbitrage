"""
Robust Mock Simulation Testing Architecture using Pytest.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.risk_manager import RiskManager
from core.unwinding import UnwindingEngine

@pytest.fixture
def mock_config():
    return {
        "TARGET_TOKENS": ["RLB"],
        "FUNDING_THRESHOLD_APR": -2.00,
        "MAX_SLIPPAGE_BPS": 50,
        "MAX_POSITION_SIZE_USD": 50000.0,
    }

@pytest.fixture
def mock_dependencies():
    mock_risk = MagicMock(spec=RiskManager)
    mock_risk.circuit_breaker_tripped = False
    mock_exec = AsyncMock()
    mock_db = AsyncMock()
    return mock_risk, mock_exec, mock_db

def test_risk_manager_bounds_enforcement(mock_config):
    """Verifies that the pre-flight risk checks reject trade payloads exceeding maximum capacity thresholds."""
    risk_manager = RiskManager(mock_config)
    assert risk_manager.validate_execution_safety("RLB", 10000, 0.20, 0.20) is True
    assert risk_manager.validate_execution_safety("RLB", 10000, 0.20, 0.25) is False # Slippage failure parameter checks
    assert risk_manager.validate_execution_safety("RLB", 60000, 0.20, 0.20) is False # Size allocation failure bounds

@pytest.mark.asyncio
async def test_unwinding_engine_circuit_breaker(mock_config, mock_dependencies):
    """Ensures the unwinding script fires a global circuit breaker if an asymmetrical execution unbalance occurs."""
    mock_risk, mock_exec, mock_db = mock_dependencies
    
    mock_exec.execute_hyperliquid_perp_short.return_value = True
    mock_exec.execute_casino_spot_buy.return_value = False # Force an asymmetric on-chain failure
    
    unwinder = UnwindingEngine(mock_config, mock_risk, mock_exec, mock_db)
    active_positions = {"RLB": {"size_usd": 5000.0, "token_address": "0x0000000000000000000000000000000000000000"}}
    current_market_data = {"RLB": {"funding_rate_apr": 0.05, "perp_price": 0.20, "casino_spot_price": 0.20}}
    
    await unwinder.monitor_and_unwind_positions(active_positions, current_market_data)
    
    mock_exec.execute_hyperliquid_perp_short.assert_called_once()
    mock_exec.execute_casino_spot_buy.assert_called_once()
    mock_risk.trigger_global_circuit_breaker.assert_called_with(
        "CRITICAL: Closed perp short hedge but failed to sell spot asset for RLB. Position is naked long!"
    )
