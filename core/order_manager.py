import MetaTrader5 as mt5
from config import LOT_SIZE, STOP_LOSS, TAKE_PROFIT, MAGIC_NUMBER, SYMBOLS, MAX_OPEN_TRADES
from core.mt5_interface import get_symbol_info_tick, get_open_positions
from utils.logger import setup_logger

logger = setup_logger("OrderManager")

class OrderManager:
    def __init__(self):
        pass

    def can_trade(self, symbol):
        """Checks if we are allowed to open a new trade for this symbol."""
        positions = get_open_positions(symbol)
        if len(positions) >= MAX_OPEN_TRADES:
            logger.info(f"Max trades ({MAX_OPEN_TRADES}) reached for {symbol}. Cannot open new.")
            return False
        return True

    def execute_action(self, symbol, action_type, atr=None, confidence=0.0):
        """
        Executes an action: BUY, SELL, CLOSE, HOLD.
        action_type: str "BUY", "SELL", "CLOSE", "HOLD"
        atr: float (optional) - used for dynamic stops
        confidence: float (optional) - used for position sizing
        """
        action_type = action_type.upper()
        
        if action_type == "HOLD":
            return True, "Held position."

        if action_type == "CLOSE":
            return self.close_all_positions(symbol)

        if action_type in ["BUY", "SELL"]:
            if not self.can_trade(symbol):
                return False, "Max trades reached."
            return self.place_market_order(symbol, action_type, atr, confidence)
            
        logger.warning(f"Unknown action: {action_type}")
        return False, "Unknown action."

    def place_market_order(self, symbol, order_type_str, atr=None, confidence=0.0):
        tick = get_symbol_info_tick(symbol)
        if not tick:
            return False, "Tick data unavailable"

        point = mt5.symbol_info(symbol).point
        
        # Position Sizing based on Confidence ("PUNCH BIGGER LOT")
        volume = LOT_SIZE
        
        # BTC Specific Multiplier (User Request: Double Lot for BTC)
        if "BTC" in symbol:
            volume = volume * 2.0
            logger.info(f"BTC Scaling: Base volume doubled to {volume}")

        if confidence >= 0.90:
            volume = 3.0 if "BTC" not in symbol else 6.0 # Scale sniper for BTC too? Or keep fixed max? 
            # User asked for "double base", let's assume aggressive scaling applies on top or we cap it.
            # Let's keep the user's specific "2.0/3.0" request for high confidence simple, 
            # changing base is safer. If confidence is high, let's just stick to the specific 2.0/3.0 hard numbers 
            # UNLESS they are smaller than the BTC base. 
            
            # actually, let's keep it simple: 
            # Base = 0.5 (Gold) -> 1.0 (BTC)
            # High Conf = 2.0 (Gold) -> 4.0 (BTC) ?? 
            # User said "let supp you take .5 so in btc take 1".
            # This implies a 2x multiplier on whatever the calculated lot is.
            pass

        # Apply Confidence Scaling
        if confidence >= 0.90:
            volume = 3.0
        elif confidence >= 0.80:
            volume = 2.0
            
        # Apply BTC Multiplier AFTER confidence or BEFORE?
        # User: "in gold let supp you take .5 so in btc take 1"
        # If High Conf Gold = 2.0, BTC should probably be 4.0.
        if "BTC" in symbol:
            volume = volume * 2.0

        if volume > LOT_SIZE:
             logger.info(f"High Confidence/BTC Scaling: Boosting volume to {volume}")

        # Dynamic Risk Calculation
        # Default fallback to config if ATR is missing or 0
        sl_points = STOP_LOSS
        tp_points = TAKE_PROFIT
        
        if atr and atr > 0:
            # User Strategy: Aggressive Scalp
            # User Strategy: Robust Agentic
            # SL: 1.5 * ATR (Wider breathing room)
            # TP: 2.0 * ATR (Reward > Risk)
            sl_dist_price = 1.5 * atr
            tp_dist_price = 2.0 * atr
            
            # Convert price distance to points
            sl_points = sl_dist_price / point
            tp_points = tp_dist_price / point
            
            logger.info(f"Dynamic Stops (ATR={atr:.2f}): SL={sl_dist_price:.2f} ({sl_points:.0f} pts), TP={tp_dist_price:.2f} ({tp_points:.0f} pts)")
        
        if order_type_str == "BUY":
            # For BUY: Ask price
            price = tick.ask
            sl = price - sl_points * point
            tp = price + tp_points * point
            mt5_type = mt5.ORDER_TYPE_BUY
        else:
            # For SELL: Bid price
            price = tick.bid
            sl = price + sl_points * point
            tp = price - tp_points * point
            mt5_type = mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20, # Slippage tolerance
            "magic": MAGIC_NUMBER,
            "comment": "ReAct Agent",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.comment}, retcode={result.retcode}")
            return False, f"MT5 Error: {result.comment}"
        
        logger.info(f"Order placed: {order_type_str} {symbol} @ {price}, Ticket={result.order}")
        return True, f"Executed {order_type_str} {symbol}"

    def close_all_positions(self, symbol):
        positions = get_open_positions(symbol)
        if not positions:
            return True, "No positions to close."

        count = 0
        for pos in positions:
            tick = get_symbol_info_tick(symbol)
            # To close a BUY, we SELL. To close a SELL, we BUY.
            # But specific closing logic usually uses the opposite price.
            # MT5 closing involves sending an opposite deal.
            
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 20,
                "magic": MAGIC_NUMBER,
                "comment": "ReAct Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close failed for ticket {pos.ticket}: {result.comment}")
            else:
                count += 1
                # Calculate approximate PnL for logging usage
                # Profit = (ClosePrice - OpenPrice) * Volume * ContractSize
                # Simplified point calculation for logging:
                diff = (price - pos.price_open) if pos.type == mt5.ORDER_TYPE_BUY else (pos.price_open - price)
                # This doesn't account for tick value perfectly but good enough for relative win/loss check
                # Actually, MT5 deals return profit? No, we have to wait for deal completion.
                # Better: Just log the close price.
                logger.info(f"[TRADE_RESULT] Symbol={symbol} Ticket={pos.ticket} Type={'BUY' if pos.type==mt5.ORDER_TYPE_BUY else 'SELL'} Open={pos.price_open} Close={price} Diff={diff:.5f}")

        return True, f"Closed {count} positions."
