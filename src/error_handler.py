import logging
import traceback

# Setup central logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LogAgent")

def handle_error(err, context=""):
    """Centralized error handling and logging."""
    logger.error(f"Error {context}: {err}")
    logger.debug(traceback.format_exc())
