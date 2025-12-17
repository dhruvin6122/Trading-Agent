try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

import pandas as pd
from datetime import datetime
from utils.logger import setup_logger
from config import MT5_PATH

logger = setup_logger("MT5Interface")

def initialize_mt5():
    """Initializes connection to the local MT5 terminal."""
    if mt5 is None:
        logger.error("MetaTrader5 library not found (Linux/Vercel Environment). Trading Disabled.")
        return False

    for i in range(3):
        try:
            connected = mt5.initialize(path=MT5_PATH) if MT5_PATH else mt5.initialize()
            if connected:
                logger.info(f"MetaTrader5 package version: {mt5.__version__}")
                logger.info(f"Terminal connected: {mt5.terminal_info().name}")
                return True
            else:
                logger.warning(f"initialize() attempt {i+1} failed, error code = {mt5.last_error()}")
                import time
                time.sleep(2)
        except Exception as e:
            logger.error(f"Exception during initialize: {e}")
            
    logger.error("All initialize attempts failed.")
    return False

def shutdown_mt5():
    if mt5:
        mt5.shutdown()
        logger.info("MT5 connection shutdown")

def get_symbol_info_tick(symbol):
    """Gets the last tick for a symbol (Bid/Ask)."""
    if mt5 is None: return None
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"{symbol} not found, can not call symbol_info_tick()")
        return None
    return tick

def get_ohlc_data(symbol, timeframe, n=100):
    """
    Fetches the last n candles.
    timeframe: e.g., mt5.TIMEFRAME_M5
    """
    if mt5 is None: return None
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    if rates is None or len(rates) == 0:
        logger.error(f"Failed to get rates for {symbol}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def get_open_positions(symbol=None):
    """Returns list of open positions, optionally filtered by symbol."""
    if mt5 is None: return []
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()
        
    if positions is None:
        return []
    return list(positions)

def get_account_info():
    if mt5 is None: return None
    return mt5.account_info()
