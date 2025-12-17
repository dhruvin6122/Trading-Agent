import os

# MetaTrader 5 Configuration
# Note: Path to terminal is usually auto-detected if not specified.
# If you have multiple MT5 instances, specify the path to terminal64.exe
MT5_PATH = None 

# Trading Parameters
SYMBOLS = ["XAUUSD+", "BTCUSD", "EURUSD+", "USDJPY+", "GBPUSD+", "GBPJPY+", "US30+"]
TIMEFRAME_STR = "M1"  # Used for log display
TIMEFRAME = 1 # M1 Timeframe
TIMEFRAME_MINUTES = 1 # Required for MarketAnalyzer map

# Risk Management (Dynamic)
# Rule: $20k Equity = 1.0 Lot.
# Formula: Lots = CurrentEquity / EQUITY_PER_1_LOT
EQUITY_PER_1_LOT = 20000.0 
MIN_LOT_GOLD = 0.20
MIN_LOT_FOREX = 0.50

# Fallback defaults
STOP_LOSS = 50.0   
TAKE_PROFIT = 80.0 
MAX_OPEN_TRADES = 3
MAGIC_NUMBER = 123456

# Production Safety (Equity Guard)
MAX_DAILY_DRAWDOWN_PERCENT = 2.0 # Tightened to 2% (Hard Stop)

# LLM Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-v3.1:671b-cloud"
TEMPERATURE = 0.0

# Logging
# Check if running on Vercel/Linux (Read-Only FS)
if os.name == 'nt':
    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
else:
    # On Serverless/Linux, ONLY /tmp is writable
    LOG_DIR = "/tmp/logs"

os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "trading_agent.log")
