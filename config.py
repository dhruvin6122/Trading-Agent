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

# Risk Management (Fixed)
LOT_SIZE = 0.1 # Reduced from 0.5. Conservative Base.
STOP_LOSS = 50.0   # Default Points (Fallback)
TAKE_PROFIT = 80.0 # Default Points (Fallback)
MAX_OPEN_TRADES = 3 # Reduced from 5 to limit exposure.
MAGIC_NUMBER = 123456

# Production Safety (Equity Guard)
MAX_DAILY_DRAWDOWN_PERCENT = 2.0 # Tightened to 2% (Hard Stop)

# LLM Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-v3.1:671b-cloud"
TEMPERATURE = 0.0

# Logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "trading_agent.log")
