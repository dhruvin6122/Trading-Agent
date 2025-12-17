import MetaTrader5 as mt5
import requests
import json
from config import MT5_PATH, OLLAMA_URL, MODEL_NAME, SYMBOLS

def check_mt5():
    print("Checking MT5 Connection...")
    if not mt5.initialize(path=MT5_PATH) if MT5_PATH else mt5.initialize():
        print(f"FAILED: MT5 initialize failed, error code = {mt5.last_error()}")
        return False
    
    print(f"SUCCESS: Connected to {mt5.terminal_info().name}")
    
    print("Checking Symbols...")
    for sym in SYMBOLS:
        selected = mt5.symbol_select(sym, True)
        if not selected:
            print(f"WARNING: Symbol {sym} not found or not visible!")
        else:
            tick = mt5.symbol_info_tick(sym)
            if tick:
                print(f"  {sym}: ASK={tick.ask} BID={tick.bid}")
            else:
                print(f"  {sym}: Selected but no tick data")
                
    mt5.shutdown()
    return True

def check_ollama():
    print("\nChecking Ollama Connection...")
    payload = {
        "model": MODEL_NAME,
        "prompt": "Say 'Ollama is ready' in JSON format like {\"status\": \"ready\"}",
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"SUCCESS: Ollama responded. Response: {response.json().get('response')}")
            return True
        else:
            print(f"FAILED: Status Code {response.status_code}")
            return False
    except Exception as e:
        print(f"FAILED: Connection Error: {e}")
        return False

if __name__ == "__main__":
    mt5_ok = check_mt5()
    ollama_ok = check_ollama()
    
    if mt5_ok and ollama_ok:
        print("\nAll Systems Go! You can run 'python main.py' now.")
    else:
        print("\nSome checks failed. Please fix before running agent.")
        import sys
        sys.exit(1)
