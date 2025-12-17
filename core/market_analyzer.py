import pandas as pd
import MetaTrader5 as mt5
from core.mt5_interface import get_ohlc_data, get_symbol_info_tick, get_open_positions
from config import TIMEFRAME_MINUTES
from utils.logger import setup_logger

logger = setup_logger("MarketAnalyzer")

# Map minutes to MT5 constants
# Add more mappings as needed
TIMEFRAME_MAP = {
    1: mt5.TIMEFRAME_M1,
    5: mt5.TIMEFRAME_M5,
    15: mt5.TIMEFRAME_M15,
    60: mt5.TIMEFRAME_H1
}

class MarketAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.mt5_timeframe = TIMEFRAME_MAP.get(TIMEFRAME_MINUTES, mt5.TIMEFRAME_M5)

    def get_market_data(self):
        """
        Fetches data for M1, M5, M15 and calculates indicators.
        Returns a rich dictionary summary.
        """
        # Timeframes to fetch
        tfs = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15
        }
        
        data = {}
        analysis_str = ""
        last_atr_m1 = 0.0

        for tf_name, tf_const in tfs.items():
            df = get_ohlc_data(self.symbol, tf_const, n=100)
            if df is None:
                continue
                
            # Calc Indicators
            df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(14).mean()
            
            # Bollinger Bands (20, 2)
            # BB_MID = EMA20 (or SMA20? Standard is SMA20) -> Using SMA20 for standard BB
            sma20 = df['close'].rolling(20).mean()
            std20 = df['close'].rolling(20).std()
            df['BB_UPPER'] = sma20 + (2.0 * std20)
            df['BB_LOWER'] = sma20 - (2.0 * std20)
            # Use SMA20 as Mid line
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            if tf_name == "M1":
                last_atr_m1 = prev['ATR']

            # Analyze Trend
            p_vs_e20 = "Above" if prev['close'] > prev['EMA_20'] else "Below"
            e20_vs_e50 = "Bullish" if prev['EMA_20'] > prev['EMA_50'] else "Bearish"
            
            # Analyze Range
            bb_width = prev['BB_UPPER'] - prev['BB_LOWER']
            in_range = "Inside" if prev['BB_LOWER'] < prev['close'] < prev['BB_UPPER'] else "Breakout"

            analysis_str += f"""
[{tf_name} Data]
Close: {prev['close']}
EMA9: {prev['EMA_9']:.2f} | EMA20: {prev['EMA_20']:.2f} | EMA50: {prev['EMA_50']:.2f}
BB: Upper={prev['BB_UPPER']:.2f} | Lower={prev['BB_LOWER']:.2f} | Width={bb_width:.2f}
Trend: {p_vs_e20} EMA20, Structure: {e20_vs_e50}
Range Status: {in_range}
"""

        tick = get_symbol_info_tick(self.symbol)
        if tick is None:
            return None
            
        current_price = tick.ask
        spread = tick.ask - tick.bid

        # Check existing positions
        positions = get_open_positions(self.symbol)
        position_summary = "No open positions."
        pnl_info = ""
        if positions:
            pos_details = []
            for p in positions:
                type_str = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
                pos_details.append(f"{type_str} @ {p.price_open} (PnL: {p.profit:.2f})")
            position_summary = "Open Positions:\n" + "\n".join(pos_details)
            
        # Construct Textual Observation
        observation = f"""
Instrument: {self.symbol}
Current Price: {current_price}
Spread: {spread:.5f}

--- MULTI-TIMEFRAME ANALYSIS ---
{analysis_str}
--------------------------------

Account/Position Status:
{position_summary}
"""
        return {
            "observation": observation.strip(),
            "atr": last_atr_m1, # Use M1 ATR for scalping stops
            "current_price": current_price,
            "open_positions": positions
        }

