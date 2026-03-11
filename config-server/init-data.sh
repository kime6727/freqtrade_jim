#!/bin/bash

CONFIG_DIR="/freqtrade/user_data"
STRATEGY_DIR="$CONFIG_DIR/strategies"
LOGS_DIR="$CONFIG_DIR/logs"
BACKUP_DIR="$CONFIG_DIR/backups"

echo "Initializing FreqTrade data directory..."

mkdir -p "$STRATEGY_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$BACKUP_DIR"

DEFAULT_CONFIG='{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 30,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "CNY",
    "timeframe": "5m",
    "dry_run": true,
    "dry_run_wallet": 1000,
    "cancel_open_orders_on_exit": false,
    "strategy": "SampleStrategy",
    "stoploss": -0.1,
    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
    },
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {
            "enabled": false,
            "bids_to_ask_delta": 1
        }
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
        "pair_blacklist": []
    },
    "pairlists": [{"method": "StaticPairList"}],
    "telegram": {"enabled": false, "token": "", "chat_id": ""},
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "jwt_secret_key": "freqtrade_jwt_secret_key_change_me",
        "ws_token": "freqtrade_ws_token_change_me",
        "CORS_origins": [],
        "username": "freqtrade",
        "password": "KJDD9773LJKDkjkj"
    },
    "bot_name": "freqtrade_bot",
    "initial_state": "running",
    "force_entry_enable": true,
    "internals": {"process_throttle_secs": 5}
}'

DEFAULT_STRATEGY='from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SampleStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short: bool = False
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.10
    timeframe = "5m"
    process_only_new_candles = True
    
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_rsi = 30
    sell_rsi = 70

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] < self.buy_rsi), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["rsi"] > self.sell_rsi), "exit_long"] = 1
        return dataframe
'

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "$DEFAULT_CONFIG" > "$CONFIG_DIR/config.json"
    echo "Created default config.json"
else
    echo "config.json already exists"
fi

if [ ! -f "$STRATEGY_DIR/SampleStrategy.py" ]; then
    echo "$DEFAULT_STRATEGY" > "$STRATEGY_DIR/SampleStrategy.py"
    echo "Created default SampleStrategy.py"
else
    echo "SampleStrategy.py already exists"
fi

echo "Initialization complete. Files in $CONFIG_DIR:"
ls -la "$CONFIG_DIR"
echo "Files in $STRATEGY_DIR:"
ls -la "$STRATEGY_DIR"
