import MetaTrader5 as mt5
import sys

if not mt5.initialize():
    print(f"Init False: {mt5.last_error()}")
    sys.exit(1)

print("Init True")
symbols = ["XAUUSD", "EURUSD", "USDJPY", "BTCUSD"]
for s in symbols:
    sel = mt5.symbol_select(s, True)
    info = mt5.symbol_info(s)
    if info is None:
        print(f"{s}: Not Found")
    else:
        print(f"{s}: Visible={sel}, Bid={info.bid}, Ask={info.ask}")

mt5.shutdown()
