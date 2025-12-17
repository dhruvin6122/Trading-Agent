import time
from core.market_analyzer import MarketAnalyzer
from core.llm_bridge import LLMBridge
from core.order_manager import OrderManager
from utils.logger import setup_logger
import MetaTrader5 as mt5
from config import MAX_DAILY_DRAWDOWN_PERCENT
from utils.logger import setup_logger

logger = setup_logger("ReActAgent")

class ReActTrader:
    def __init__(self, symbols):
        self.symbols = symbols
        self.llm = LLMBridge()
        self.order_manager = OrderManager()
        self.analyzers = {s: MarketAnalyzer(s) for s in symbols}

    def run_cycle(self):
        """Runs one ReAct cycle for all symbols."""
        logger.info("Starting ReAct Cycle...")
        
        # --- EQUITY GUARD CHECK ---
        account_info = mt5.account_info()
        if account_info:
            current_equity = account_info.equity
            
            # Initialize start of day equity if not set (or could be reset daily in a real production env)
            if not hasattr(self, 'start_equity') or self.start_equity is None:
                self.start_equity = current_equity
                logger.info(f"Daily Equity Guard Initialized: ${self.start_equity:.2f}")

            # Calculate Drawdown
            drawdown = (self.start_equity - current_equity) / self.start_equity * 100
            
            if drawdown >= MAX_DAILY_DRAWDOWN_PERCENT:
                logger.critical(f"EQUITY GUARD TRIGGERED! Drawdown {drawdown:.2f}% > Limit {MAX_DAILY_DRAWDOWN_PERCENT}%. HALTING AGENT.")
                raise SystemExit("Equity Guard Triggered - Trading Halted.")
                
        # ---------------------------
        
        for symbol in self.symbols:
            try:
                self.process_symbol(symbol)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

        logger.info("Cycle completed.")

    def process_symbol(self, symbol):
        logger.info(f"--- Analyzing {symbol} ---")
        
        # 1. Observe
        analyzer = self.analyzers[symbol]
        market_state = analyzer.get_market_data()
        
        if not market_state:
            logger.warning(f"No market data for {symbol}, skipping.")
            return

        observation = market_state["observation"]
        atr_value = market_state.get("atr", 0.0)
        
        # --- PASSIVE MANAGEMENT: Check Trailing Stops / Break Even ---
        # We do this every cycle regardless of LLM Decision
        if atr_value > 0:
            self.order_manager.manage_risk(symbol, atr_value)
        # -------------------------------------------------------------
        
        logger.info(f"Observation:\n{observation}")

        # 2. Reason (Ask LLM)
        decision = self.llm.get_decision(observation)
        
        thought = decision.get("thought", "No thought provided")
        action = decision.get("action", "HOLD")
        confidence = decision.get("confidence", 0.0)
        
        # --- RESILIENCY FILTER (Hard Logic Override) ---
        # Prevent degenerate trades based on RSI extremes
        rsi_value = market_state.get("rsi", 50.0)
        original_action = action
        
        if action == "BUY" and rsi_value > 70:
            action = "HOLD"
            logger.warning(f"RESILIENCY FILTER: Blocked BUY on {symbol} (RSI {rsi_value:.2f} > 70 - Overbought)")
            
        elif action == "SELL" and rsi_value < 30:
            action = "HOLD"
            logger.warning(f"RESILIENCY FILTER: Blocked SELL on {symbol} (RSI {rsi_value:.2f} < 30 - Oversold)")
            
        if action != original_action:
            thought += " [BLOCKED BY RSI FILTER]"
        # -----------------------------------------------
        
        logger.info(f"Agent Thought: {thought}")
        logger.info(f"Agent Decision: {action} (Confidence: {confidence})")

        # 3. Act & Observe Result
        # Only act if confidence is reasonable (e.g., > 0.5) or logic dictates
        # For this implementation, we trust the LLM's action if valid.
        
        success, message = self.order_manager.execute_action(symbol, action, atr=atr_value, confidence=confidence)
        logger.info(f"Action Result: {message}")
        
        # (Optional) We could feed the result back to the LLM for self-correction in a more complex loop,
        # but for this V1 we just log it.
