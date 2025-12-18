import os

# MetaTrader 5 Configuration
# Note: Path to terminal is usually auto-detected if not specified.
# If you have multiple MT5 instances, specify the path to terminal64.exe
MT5_PATH = None 

# Trading Parameters
SYMBOLS = ["XAUUSD", "BTCUSD"] # Exact symbols as requested
TIMEFRAME_STR = "M1"  
TIMEFRAME = 1 
TIMEFRAME_MINUTES = 1 # Restoring required variable 

# Risk Management
# User Request: Fixed 5.0 Lots. No Dynamic Sizing.
USE_DYNAMIC_SIZING = False
LOT_SIZE = 2.0
MAX_OPEN_TRADES = 1 # Max 1 per symbol as requested

# Fallback defaults
STOP_LOSS = 50.0   
TAKE_PROFIT = 80.0 
MAGIC_NUMBER = 123456

# Production Safety (Equity Guard)
MAX_DAILY_DRAWDOWN_PERCENT = 10.0 # Increased to 10% to allow 5-Lot volatility.

# Logging
# Check if running on Vercel/Linux (Read-Only FS)
if os.name == 'nt':
    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
else:
    # On Serverless/Linux, ONLY /tmp is writable
    LOG_DIR = "/tmp/logs"

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "trading_agent.log")
