import MetaTrader5 as mt5
import time

if not mt5.initialize():
    print("Init failed")
else:
    symbol = "XAUUSD+" 
    # Check if exists, else try XAUUSD
    if not mt5.symbol_select(symbol, True):
        print(f"{symbol} not found, trying XAUUSD")
        symbol = "XAUUSD"
        mt5.symbol_select(symbol, True)
    
    info = mt5.symbol_info(symbol)
    if info:
        print(f"Symbol: {info.name}")
        print(f"Point: {info.point}")
        print(f"Digits: {info.digits}")
        print(f"Spread: {info.spread}")
        print(f"Stops Level: {info.trade_stops_level}")
        print(f"Freeze Level: {info.trade_freeze_level}")
        print(f"Ask: {info.ask}")
        print(f"Bid: {info.bid}")
        
        # Calculate proposed SL distance
        # Config says 50 points
        sl_dist = 50 * info.point
        print(f"Proposed SL Distance (50 points): {sl_dist}")
        
        # Stops level usually in points
        min_stop_dist = info.trade_stops_level * info.point
        print(f"Min Stop Distance: {min_stop_dist}")
        
        if sl_dist < min_stop_dist:
            print("WARNING: SL is too close!")
    else:
        print("Symbol info is None")
        
    mt5.shutdown()
