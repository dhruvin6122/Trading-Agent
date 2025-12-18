import time
import schedule
import sys
from config import SYMBOLS
from core.mt5_interface import initialize_mt5, shutdown_mt5
from agent.rule_scalper import RuleBasedScalper
from utils.logger import setup_logger

logger = setup_logger("Main")

def job():
    agent.run_cycle()

if __name__ == "__main__":
    if not initialize_mt5():
        sys.exit(1)

    try:
        logger.info("Starting Rule-Based Scalper (No AI Model)...")
        agent = RuleBasedScalper(SYMBOLS)
        
        # Schedule the job to run every minute (or 5 minutes based on candle close)
        # We run M1 check.
        schedule.every(1).minutes.do(job)
        
        logger.info("Agent started. Running schedule...")
        
        # Run once immediately on startup
        job()
        
        while True:
            schedule.run_pending()
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping agent...")
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        shutdown_mt5()
