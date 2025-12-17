import MetaTrader5 as mt5
import time

print("Attempting init with default path...")
if not mt5.initialize():
    print(f"Default init failed: {mt5.last_error()}")
    
    # Try creating a dummy path just in case, but really we should try to find the real one.
    # Usually clean installs are at C:\Program Files\MetaTrader 5\terminal64.exe
    paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\Deriv\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"
    ]
    
    for p in paths:
        print(f"Trying path: {p}")
        if mt5.initialize(path=p):
            print(f"Success with {p}")
            mt5.shutdown()
            break
        else:
            print(f"Failed with {p}: {mt5.last_error()}")

else:
    print("Default init success")
    print(mt5.terminal_info())
    mt5.shutdown()
