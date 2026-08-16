## Insitutional Level Production Code - Comprehensive Mainnet-Ready Implementations

## Setup & Deployment Check sequence

## 1. Database layer verification: Ensure you have an active local Redis container listening on port 6379:

docker run --name arb-redis -p 6379:6379 -d redis

## 2. Library Installation: Standard compilation setup via lockfiles:

pip install -r requirements.txt

## 3. Run Suite Tests: Execute local offline test sequences to assert circuit breaker compliance models before routing transactions on live networks:

pytest tests/test_arbitrage.py

## 4. Mainnet Execution: Hydrate secure production variables via terminal environments and launch your bot:

export WALLET_PRIVATE_KEY="your-actual-private-key"
export WEB3_RPC_URL="your-alchemy-or-quicknode-endpoint"
python main.py

## To do:

Build out custom tracking components or historical metrics logging metrics into the Redis engine layer to monitor your cumulative realized funding PnL.
