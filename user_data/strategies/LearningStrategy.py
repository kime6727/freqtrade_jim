# FreqTrade 学习策略 - 详细注释版
# 这个策略包含了所有常用的配置和参数说明

import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta


class LearningStrategy(IStrategy):
    """
    学习策略 - 包含详细注释，适合新手学习
    
    策略逻辑：
    - 使用 RSI 指标判断超买超卖
    - RSI < 30 时买入（超卖）
    - RSI > 70 时卖出（超买）
    """
    
    # ==================== 基本配置 ====================
    
    # 策略版本（保持为3）
    INTERFACE_VERSION = 3
    
    # K线周期：1m, 5m, 15m, 1h, 4h, 1d
    timeframe = "5m"
    
    # 是否允许做空（True = 可以做空）
    can_short = False
    
    # 策略启动需要的K线数量（用于计算指标）
    startup_candle_count = 200
    
    # ==================== 止损配置 ====================
    
    # 固定止损：亏损10%自动卖出
    # 例如：买入价100，跌到90自动卖出
    stoploss = -0.10
    
    # 追踪止损配置（可选）
    trailing_stop = False                    # 是否启用追踪止损
    # trailing_stop_positive = 0.02          # 盈利2%后开始追踪
    # trailing_stop_positive_offset = 0.03   # 盈利3%后才启动追踪
    # trailing_only_offset_is_reached = True # 只有达到offset后才启动
    
    # ==================== 止盈配置 ====================
    
    # 最小收益率目标（ROI = Return on Investment）
    # 格式："分钟数": 目标收益率
    minimal_roi = {
        "0": 0.10,      # 立即：盈利10%卖出
        "30": 0.05,     # 30分钟后：盈利5%卖出
        "60": 0.03,     # 60分钟后：盈利3%卖出
        "120": 0.01     # 120分钟后：盈利1%卖出
    }
    
    # 如果不想自动止盈，设置为：
    # minimal_roi = {"0": 100}  # 100%才卖出（基本不会触发）
    
    # ==================== 信号配置 ====================
    
    # 是否使用卖出信号
    use_exit_signal = True
    
    # 是否只在盈利时才卖出
    exit_profit_only = False
    
    # 如果有买入信号，是否忽略ROI
    ignore_roi_if_entry_signal = False
    
    # ==================== 订单配置 ====================
    
    # 订单类型
    order_types = {
        "entry": "limit",        # 买入：限价单
        "exit": "limit",         # 卖出：限价单
        "stoploss": "market",    # 止损：市价单
        "stoploss_on_exchange": False
    }
    
    # 订单有效期
    order_time_in_force = {
        "entry": "GTC",          # Good Till Cancelled
        "exit": "GTC"
    }
    
    # ==================== 可优化参数 ====================
    # 这些参数可以通过 hyperopt 进行优化
    
    # RSI 买入阈值（默认30，可优化范围20-40）
    buy_rsi = IntParameter(20, 40, default=30, space="buy")
    
    # RSI 卖出阈值（默认70，可优化范围60-80）
    sell_rsi = IntParameter(60, 80, default=70, space="sell")
    
    # ==================== 指标计算 ====================
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算技术指标
        这个方法会在每个K线上运行
        """
        
        # RSI 指标（相对强弱指数）
        # 范围 0-100，<30 超卖，>70 超买
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD 指标
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']           # MACD线
        dataframe['macdsignal'] = macd['macdsignal']  # 信号线
        dataframe['macdhist'] = macd['macdhist']   # 柱状图
        
        # 布林带
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2, nbdevdn=2)
        dataframe['bb_lowerband'] = bollinger['lowerband']  # 下轨
        dataframe['bb_middleband'] = bollinger['middleband']  # 中轨
        dataframe['bb_upperband'] = bollinger['upperband']  # 上轨
        
        # SMA 简单移动平均线
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        
        # EMA 指数移动平均线
        dataframe['ema_12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_26'] = ta.EMA(dataframe, timeperiod=26)
        
        # 成交量
        dataframe['volume'] = dataframe['volume']
        
        return dataframe
    
    # ==================== 买入信号 ====================
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义买入条件
        当所有条件满足时，会触发买入信号
        """
        
        # 条件1：RSI < 30（超卖）
        # 条件2：收盘价 < 布林带下轨（价格偏低）
        # 条件3：成交量 > 0
        
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_rsi.value) &           # RSI超卖
                (dataframe['close'] < dataframe['bb_lowerband']) &  # 价格低于布林带下轨
                (dataframe['volume'] > 0)                           # 有成交量
            ),
            'enter_long'] = 1  # 设置买入信号
        
        return dataframe
    
    # ==================== 卖出信号 ====================
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义卖出条件
        当所有条件满足时，会触发卖出信号
        """
        
        # 条件1：RSI > 70（超买）
        # 条件2：收盘价 > 布林带上轨（价格偏高）
        
        dataframe.loc[
            (
                (dataframe['rsi'] > self.sell_rsi.value) &          # RSI超买
                (dataframe['close'] > dataframe['bb_upperband'])    # 价格高于布林带上轨
            ),
            'exit_long'] = 1  # 设置卖出信号
        
        return dataframe
    
    # ==================== 高级功能（可选） ====================
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, 
                           rate: float, time_in_force: str, current_time: datetime,
                           entry_tag: str, side: str, **kwargs) -> bool:
        """
        买入前的最后确认
        返回 True 允许买入，False 拒绝买入
        """
        # 可以在这里添加额外的检查逻辑
        return True
    
    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, 
                          amount: float, rate: float, time_in_force: str,
                          exit_reason: str, current_time: datetime, **kwargs) -> bool:
        """
        卖出前的最后确认
        返回 True 允许卖出，False 拒绝卖出
        """
        return True
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, 
                        after_fill: bool, **kwargs) -> float:
        """
        自定义止损逻辑
        可以根据盈利情况动态调整止损
        """
        # 示例：盈利5%后，将止损调整到成本价
        if current_profit > 0.05:
            return 0.0  # 保本止损
        
        # 使用默认止损
        return self.stoploss
    
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs) -> str:
        """
        自定义卖出逻辑
        返回卖出原因字符串，或 None 表示不卖出
        """
        # 示例：持币超过3天且盈利，强制卖出
        if trade.open_date_utc < current_time - timedelta(days=3):
            if current_profit > 0:
                return "force_exit_3days"
        
        return None
