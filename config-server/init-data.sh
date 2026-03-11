#!/bin/bash

CONFIG_DIR="/freqtrade/user_data"
STRATEGY_DIR="$CONFIG_DIR/strategies"
LOGS_DIR="$CONFIG_DIR/logs"

mkdir -p "$STRATEGY_DIR"
mkdir -p "$LOGS_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'CONFIG_EOF'
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 30,
    "tradable_balance_ratio": 0.99,
    "timeframe": "5m",
    "dry_run": true,
    "dry_run_wallet": 1000,
    "strategy": "SampleStrategy",
    "stoploss": -0.1,
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
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
        "jwt_secret_key": "freqtrade_jwt_secret",
        "ws_token": "freqtrade_ws_token",
        "username": "freqtrade",
        "password": "KJDD9773LJKDkjkj"
    },
    "bot_name": "freqtrade_bot",
    "initial_state": "running"
}
CONFIG_EOF
    echo "Created default config.json"
fi

if [ ! -f "$STRATEGY_DIR/SampleStrategy.py" ]; then
    cat > "$STRATEGY_DIR/SampleStrategy.py" << 'STRATEGY_EOF'
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SampleStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short: bool = False
    
    minimal_roi = {"0": 0.10}
    stoploss = -0.10
    timeframe = '5m'
    
    buy_rsi = 30
    sell_rsi = 70

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] < self.buy_rsi), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe['rsi'] > self.sell_rsi), 'exit_long'] = 1
        return dataframe
STRATEGY_EOF
    echo "Created SampleStrategy.py"
fi

echo "Initialization complete"
