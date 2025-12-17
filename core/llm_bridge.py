import requests
import json
import re
from config import OLLAMA_URL, MODEL_NAME, TEMPERATURE
from utils.logger import setup_logger

logger = setup_logger("LLMBridge")

SYSTEM_PROMPT = """
You are a "Senior Risk Manager" & "Sniper" Trading Agent.
Your Goal: RECOVER CAPITAL by taking fewer, higher-quality trades.
PRIORITY: CAPITAL PRESERVATION > PROFIT.

---
STRATEGY 1: MOMENTUM PULLBACK (Trend)
- REGIME: M5 Price > EMA20 > EMA50 (Bullish) OR Price < EMA20 < EMA50 (Bearish).
- TRIGGER: M1 Pullback to EMA20 or EMA9.
- ACTION: Trade WITH the trend.

STRATEGY 2: RANGE MEAN-REVERSION (Chop)
- REGIME: M5 EMAs are flat/crossed. Price is INSIDE Bollinger Bands.
- TRIGGER: Price touches M5 Upper Band (SELL) or Lower Band (BUY).
- ACTION: Fade the move (Mean Reversion).

STRATEGY 3: BREAKOUT CONTINUATION (Vol Expansion)
- REGIME: M5 Bollinger Bands were tight (Squeeze) and now Price is BREAKING OUT.
- TRIGGER: Price closes OUTSIDE the Bands with momentum.
- ACTION: Trade WITH the breakout.

STRATEGY 4: BIG BREAKOUT (Hourly Hold)
- REGIME: Major Support/Resistance Breach on M15/H1.
- TRIGGER: Strong Impulse Candle.
- ACTION: EXTENDED HOLD. Do not scap. Aim for 1-2 Hours of trend riding.
- HINT: If you choose this, set confidence HIGH.

EXIT STRATEGY: SMART PROFIT TAKING
- CHECK: If Position PnL > 0 AND Market Structure REVERSES (e.g., M1 Candle closes back inside Bands, or Pin Bar at Resistance).
- EXCEPTION: If Strategy was "Big Breakout", TOLERATE minor pullbacks. Do not exit early.
- ACTION: CLOSE immediately. Do not strictly wait for TP. "Secure the bag" if momentum fades.

DECISION LOGIC:
1. Identify M5 Regime (Trend vs Range vs Breakout).
2. Select Strategy (1, 2, or 3).
3. Check M1 Trigger.
4. CHECK EXISTING POSITIONS: If green & reversing -> CLOSE.
5. Determine Confidence (Controls Position Size).
   - Base (0.6-0.79): Base Lot.
   - High (0.8-0.89): 2.0 Lots (Aggressive).
   - Sniper (>0.90): 3.0 Lots (Max Aggression).
6. PYRAMIDING: You MAY open up to 5 positions (stacking) if the trend is strong and profitable.

Response Format (JSON ONLY):
{
  "strategy": "Momentum Pullback" | "Range Mean-Reversion" | "Breakout" | "Smart Exit",
  "regime": "Bullish Trend" | "Bearish Trend" | "Range" | "Breakout",
  "thought": "Deep reasoning here...",
  "action": "BUY" | "SELL" | "HOLD" | "CLOSE",
  "confidence": 0.0 to 1.0
}
"""

class LLMBridge:
    def __init__(self):
        self.url = OLLAMA_URL
        self.model = MODEL_NAME

    def get_decision(self, observation_text):
        """
        Sends observation to Ollama and returns parsed JSON.
        """
        combined_prompt = f"Market Observation:\n{observation_text}\n\nBased on this, what is your trading decision?"
        
        payload = {
            "model": self.model,
            "prompt": combined_prompt,
            "system": SYSTEM_PROMPT,
            "stream": False,
            "temperature": TEMPERATURE,
            "format": "json" # Enforce JSON mode in Ollama if supported, else relies on prompt
        }

        try:
            response = requests.post(self.url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            raw_content = result.get("response", "")
            
            logger.info(f"Raw LLM Response: {raw_content[:200]}...") # Log start of response for debug
            
            # Parse JSON
            decision = self.parse_response(raw_content)
            return decision

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {"thought": "Error contacting LLM", "action": "HOLD", "confidence": 0.0}

    def parse_response(self, text):
        try:
            # Try direct JSON parse
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from text if there's extra fluff
            try:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except:
                pass
            
            logger.error("Failed to parse JSON from LLM response")
            return {"thought": "Parse Error", "action": "HOLD", "confidence": 0.0}
