#!/bin/bash

CONFIG_DIR="/freqtrade/user_data"
STRATEGY_DIR="$CONFIG_DIR/strategies"
LOGS_DIR="$CONFIG_DIR/logs"

mkdir -p "$STRATEGY_DIR"
mkdir -p "$LOGS_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo '{"max_open_trades":3,"stake_currency":"USDT","stake_amount":30,"tradable_balance_ratio":0.99,"fiat_display_currency":"CNY","timeframe":"5m","dry_run":true,"cancel_open_orders_on_exit":false,"strategy":"SampleStrategy","stoploss":-0.1,"unfilledtimeout":{"entry":10,"exit":10,"exit_timeout_count":0,"unit":"minutes"},"entry_pricing":{"price_side":"same","use_order_book":true,"order_book_top":1,"price_last_balance":0.0,"check_depth_of_market":{"enabled":false,"bids_to_ask_delta":1}},"exit_pricing":{"price_side":"same","use_order_book":true,"order_book_top":1},"exchange":{"name":"binance","key":"","secret":"","ccxt_config":{},"ccxt_async_config":{},"pair_whitelist":["BTC/USDT","ETH/USDT"],"pair_blacklist":[]},"pairlists":[{"method":"StaticPairList"}],"telegram":{"enabled":false,"token":"","chat_id":""},"api_server":{"enabled":true,"listen_ip_address":"0.0.0.0","listen_port":8080,"verbosity":"error","jwt_secret_key":"freqtrade_jwt_secret","ws_token":"freqtrade_ws_token","CORS_origins":[],"username":"freqtrade","password":"KJDD9773LJKDkjkj"},"bot_name":"freqtrade_bot","initial_state":"running","force_entry_enable":true,"internals":{"process_throttle_secs":5}}' > "$CONFIG_DIR/config.json"
    echo "Created default config.json"
fi

if [ ! -f "$STRATEGY_DIR/SampleStrategy.py" ]; then
    cat > "$STRATEGY_DIR/SampleStrategy.py" << 'STRATEGY_EOF'
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SampleStrategy(IStrategy):
    minimal_roi = {"0": 0.10}
    stoploss = -0.10
    timeframe = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] < 30), 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > 70), 'sell'] = 1
        return dataframe
STRATEGY_EOF
    echo "Created SampleStrategy.py"
fi

echo "Initialization complete"
