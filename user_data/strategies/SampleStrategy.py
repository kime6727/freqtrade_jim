from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SampleStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short: bool = False
    
    minimal_roi = {
        "0": 0.10
    }
    stoploss = -0.10
    timeframe = '5m'
    process_only_new_candles = True
    
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    buy_rsi = 30
    sell_rsi = 70

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] < self.buy_rsi),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe['rsi'] > self.sell_rsi),
            'exit_long'
        ] = 1
        return dataframe
