import MetaTrader5 as mt5
import sys

try:
    print("Initialize...")
    if not mt5.initialize():
        print(f"ERROR_CODE:{mt5.last_error()}")
        sys.exit(1)
    else:
        print("SUCCESS")
        mt5.shutdown()
except Exception as e:
    print(f"EXCEPTION:{e}")
