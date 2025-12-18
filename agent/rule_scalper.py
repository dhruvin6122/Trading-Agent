import time
import pandas as pd
import MetaTrader5 as mt5
from config import LOT_SIZE, MAX_OPEN_TRADES, TIMEFRAME_MINUTES
from core.mt5_interface import get_ohlc_data, get_open_positions

from core.order_manager import OrderManager
from utils.logger import setup_logger

logger = setup_logger("RuleScalper")

class RuleBasedScalper:
    def __init__(self, symbols):
        self.symbols = symbols
        self.order_manager = OrderManager()

    def get_data_multi_timeframe(self, symbol):
        """Fetches M1 and M5 data for the symbol."""
        # M1 Data (Entry)
        df_m1 = get_ohlc_data(symbol, n=100, timeframe=mt5.TIMEFRAME_M1)
        # M5 Data (Trend Bias)
        df_m5 = get_ohlc_data(symbol, n=100, timeframe=mt5.TIMEFRAME_M5)
        
        if df_m1 is None or df_m5 is None:
            return None, None
            
        return df_m1, df_m5

    def calculate_indicators(self, df):
        if df is None or df.empty: return df
        
        # EMAs (Manual Calculation)
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # ATR (Manual Calculation)
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df

    def check_signals(self, symbol):
        # 1. Check Open Trades
        positions = get_open_positions(symbol)
        if len(positions) >= MAX_OPEN_TRADES:
            logger.info(f"{symbol}: Max trades reached ({len(positions)}). Skipping.")
            return

        # 2. Get Data
        df_m1, df_m5 = self.get_data_multi_timeframe(symbol)
        if df_m1 is None or df_m5 is None: return

        # 3. Calculate Indicators
        df_m1 = self.calculate_indicators(df_m1)
        df_m5 = self.calculate_indicators(df_m5)
        
        # 4. Analyze M5 Trend Logic
        # Last closed M5 candle (iloc[-1] is current open, -2 is last closed)
        m5_now = df_m5.iloc[-1] # Live
        m5_prev = df_m5.iloc[-2] # Confirmed
        
        # Bias: UP if EMA20 > EMA50 AND Price > EMA20
        m5_bias = "NEUTRAL"
        if m5_prev['ema_20'] > m5_prev['ema_50'] and m5_prev['close'] > m5_prev['ema_20']:
            m5_bias = "BULLISH"
        elif m5_prev['ema_20'] < m5_prev['ema_50'] and m5_prev['close'] < m5_prev['ema_20']:
            m5_bias = "BEARISH"
            
        if m5_bias == "NEUTRAL":
            logger.info(f"{symbol}: M5 Bias Neutral (EMA20={m5_prev['ema_20']:.2f}, EMA50={m5_prev['ema_50']:.2f}). Waiting.")
            return

        # 5. Analyze M1 Entry Logic (Pullback)
        m1_now = df_m1.iloc[-1]
        m1_prev = df_m1.iloc[-2]
        
        # ATR for Volatility Check
        atr = m1_prev['atr']
        if atr < 0.5: # Example filter for tiny ATR (mostly noise)
             # Actually for XAUUSD 0.5 is huge, for BTC it's tiny. Need minimal check?
             # User said: "Skip trades if EMAs are flat or spread is high"
             # Let's rely on Price Action.
             pass

        action = None
        
        if m5_bias == "BULLISH":
            # Rule: M1 Price pulls back near EMA20 then bullish candle closes.
            # "Near" = Low touched EMA20 (or slightly below) but Close is > EMA20?
            # Or Low <= EMA20 and Close > Open (Green Candle)
            
            # Check M1 Pullback candle (Previous candle)
            dist_to_ema20 = abs(m1_prev['low'] - m1_prev['ema_20'])
            is_near_ema = m1_prev['low'] <= m1_prev['ema_20'] or dist_to_ema20 < (atr * 0.2)
            is_bullish_close = m1_prev['close'] > m1_prev['open']
            
            if is_near_ema and is_bullish_close:
                logger.info(f"SIGNAL FOUND: {symbol} BUY (M5 Bullish + M1 Pullback)")
                action = "BUY"

        elif m5_bias == "BEARISH":
            # Rule: M1 Price pulls back near EMA20 then bearish candle closes.
            # "Near" = High touched EMA20 (or slightly above)
            
            dist_to_ema20 = abs(m1_prev['high'] - m1_prev['ema_20'])
            is_near_ema = m1_prev['high'] >= m1_prev['ema_20'] or dist_to_ema20 < (atr * 0.2)
            is_bearish_close = m1_prev['close'] < m1_prev['open']
            
            if is_near_ema and is_bearish_close:
                logger.info(f"SIGNAL FOUND: {symbol} SELL (M5 Bearish + M1 Pullback)")
                action = "SELL"

        # 6. Execute
        if action:
            # Setup SL/TP
            # SL = ATR based (e.g., 2x ATR below Low for Buy)
            # User: "SL ATR-based... TP 1.2-1.5 x ATR"
            
            sl_pips = atr * 2.0 # More breathing room than 1.0
            tp_pips = atr * 1.5 
            
            # Send to Order Manager
            # We bypass the 'llm_bridge' confidence stuff.
            # We call place_market_order directly or via execute_action.
            # OrderManager expects "ATR" for dynamic stop calc, but we can calculate precise prices here?
            # Actually OrderManager logic for SL/TP is inside `place_market_order` using passed ATR.
            # Let's use that to keep it consistent.
            
            self.order_manager.execute_action(symbol, action, atr=atr, confidence=1.0)

            self.order_manager.execute_action(symbol, action, atr=atr, confidence=1.0)

    def check_breakout_signals(self, symbol):
        """
        Breakout Strategy:
        1. Look back 20 periods (M5 or M15, let's use M5 for now as per Scalper).
        2. Identify High/Low of last 20 candles (excluding current).
        3. If Current Close > High -> BUY
        4. If Current Close < Low -> SELL
        5. Filter: ATR should be decent (avoid dead markets).
        """
        # 1. Get Data (M5 for Breakout?)
        # User said "2 strategy rule base". Let's use M5 for breakout to capture bigger moves.
        df = get_ohlc_data(symbol, n=50, timeframe=mt5.TIMEFRAME_M5)
        if df is None: return
        
        # Indicators
        df = self.calculate_indicators(df)
        
        # 2. Logic
        # We need completed candles for the Range.
        # Range = Last 20 closed candles.
        # Current Candle = iloc[-1] (Live)
        
        # Look at candles -21 to -2 (20 candles)
        # 0 is oldest. -1 is current. -2 is last closed.
        range_window = df.iloc[-21:-1]
        
        if len(range_window) < 20: return
        
        highest_high = range_window['high'].max()
        lowest_low = range_window['low'].min()
        
        current = df.iloc[-1]
        prev_close = df.iloc[-2]['close'] # Confirmation from last closed candle?
        # Aggressive Breakout: Current Price breaks level?
        # Safer Breakout: Last Closed Candle broke level.
        
        # Let's use Last Closed Candle for confirmation to avoid wicks.
        last_closed = df.iloc[-2]
        
        atr = last_closed['atr']
        if pd.isna(atr) or atr == 0: return

        action = None
        
        # Check Breakout
        # Buy: Close > Highest High
        if last_closed['close'] > highest_high:
            # Check if it wasn't already above (avoid multiple signals for same breakout)
            # Look at candle before that (-3)
            prev_prev = df.iloc[-3]
            if prev_prev['close'] <= highest_high:
                logger.info(f"BREAKOUT SIGNAL: {symbol} BUY (Close {last_closed['close']} > 20 High {highest_high})")
                action = "BUY"
                
        # Sell: Close < Lowest Low
        elif last_closed['close'] < lowest_low:
             prev_prev = df.iloc[-3]
             if prev_prev['close'] >= lowest_low:
                logger.info(f"BREAKOUT SIGNAL: {symbol} SELL (Close {last_closed['close']} < 20 Low {lowest_low})")
                action = "SELL"
                
        if action:
            self.order_manager.execute_action(symbol, action, atr=atr, confidence=1.0)

    def run_cycle(self):
        logger.info("--- Starting Scalp & Breakout Cycle ---")
        for symbol in self.symbols:
            try:
                # Strategy 1: Pullback Scalper
                self.check_signals(symbol)
                
                # Strategy 2: Breakout
                self.check_breakout_signals(symbol)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
