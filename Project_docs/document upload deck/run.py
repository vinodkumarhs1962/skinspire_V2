# run.py
import os
import sys
import logging
import signal
from typing import Optional

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".flaskenv")
except ImportError:
    logger.warning("python-dotenv not installed. Proceeding with existing environment variables.")

def run_flask_app(
    host: Optional[str] = None, 
    port: Optional[int] = None, 
    debug: Optional[bool] = None
):
    """
    Run Flask application with explicit configuration
    
    Args:
        host (str, optional): Host to bind the server
        port (int, optional): Port to run the server
        debug (bool, optional): Enable debug mode
    """
    try:
        from app import create_app
    except ImportError as e:
        logger.error(f"Could not import Flask application: {e}")
        sys.exit(1)

    # Create the application
    app = create_app()

    # Determine configuration
    host = host or os.environ.get('FLASK_HOST', '127.0.0.1')
    port = port or int(os.environ.get('FLASK_PORT', '5000'))
    
    # Determine debug mode
    if debug is None:
        debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    logger.info(f"Starting application on {host}:{port}")
    logger.info(f"Debug mode: {'enabled' if debug else 'disabled'}")

    # Run the application
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Error running Flask application: {e}")
        sys.exit(1)

def main():
    """
    Main entry point for the application
    """
    try:
        # Setup signal handling for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Interrupt received. Shutting down...")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run the application
        run_flask_app()
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()