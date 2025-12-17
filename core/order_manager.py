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
        
        # Position Sizing based on Confidence (Conservative Scaling)
        volume = LOT_SIZE
        
        # Moderate Confidence Scaling
        if confidence >= 0.90:
            volume = LOT_SIZE * 1.5
        elif confidence >= 0.80:
            volume = LOT_SIZE * 1.2
            
        # BTC Multiplier - Removed Aggressive Double Scaling
        # We rely on the Base Lot being set correctly in Config for the account size.
        
        if volume > LOT_SIZE:
             logger.info(f"Confidence Scaling: Boosting volume to {volume}")

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

    def manage_risk(self, symbol, atr):
        """
        Adjusts SL/TP for open positions:
        1. Break Even: If Price > Entry + 0.5*ATR, move SL to Entry.
        2. Trailing Stop: If Price > Entry + 1.0*ATR, Trail SL at 0.5*ATR distance.
        """
        if not atr or atr <= 0:
            return
            
        positions = get_open_positions(symbol)
        if not positions:
            return

        tick = get_symbol_info_tick(symbol)
        if not tick: return
        
        point = mt5.symbol_info(symbol).point
        be_trigger_dist = 0.5 * atr
        trail_trigger_dist = 1.0 * atr
        trail_dist = 0.5 * atr # Trail behind by 0.5 ATR

        for pos in positions:
            # Check for BUY
            if pos.type == mt5.ORDER_TYPE_BUY:
                current_profit_dist = tick.bid - pos.price_open
                
                # Check Break Even
                if current_profit_dist > be_trigger_dist:
                    new_sl = pos.price_open + (10 * point) # Entry + small buffer (spread cover)
                    
                    # Only modify if new SL is better than current SL
                    if pos.sl < new_sl: # Current SL is below target (worse)
                        # Check Trailing
                        if current_profit_dist > trail_trigger_dist:
                            # Trail: Price - TrailDist
                            trail_sl = tick.bid - trail_dist
                            if trail_sl > new_sl:
                                new_sl = trail_sl
                                
                        # Execute Modification
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": pos.ticket,
                            "symbol": symbol,
                            "sl": new_sl,
                            "tp": pos.tp, # Keep TP same
                            "magic": MAGIC_NUMBER,
                        }
                        res = mt5.order_send(request)
                        if res.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"Managed Risk {symbol} #{pos.ticket}: SL moved to {new_sl} (Profit Dist: {current_profit_dist:.5f})")

            # Check for SELL
            elif pos.type == mt5.ORDER_TYPE_SELL:
                current_profit_dist = pos.price_open - tick.ask
                
                # Check Break Even
                if current_profit_dist > be_trigger_dist:
                    new_sl = pos.price_open - (10 * point) # Entry - small buffer
                    
                    # For Sell, "Better" SL is LOWER price. Current SL > New SL means we tighten it down.
                    if pos.sl == 0.0 or pos.sl > new_sl: 
                        # Check Trailing
                        if current_profit_dist > trail_trigger_dist:
                            # Trail: Price + TrailDist
                            trail_sl = tick.ask + trail_dist
                            if trail_sl < new_sl:
                                new_sl = trail_sl
                                
                        # Execute Modification
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": pos.ticket,
                            "symbol": symbol,
                            "sl": new_sl,
                            "tp": pos.tp,
                            "magic": MAGIC_NUMBER,
                        }
                        res = mt5.order_send(request)
                        if res.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"Managed Risk {symbol} #{pos.ticket}: SL moved to {new_sl} (Profit Dist: {current_profit_dist:.5f})")
