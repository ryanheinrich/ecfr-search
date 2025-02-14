from ecfr_manager import ECFRManager
import sys
import logging

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        ecfr = ECFRManager()
        logger.info("Starting eCFR download process...")
        success = ecfr.download_ecfr()
        
        if success:
            logger.info("Download completed successfully!")
        else:
            logger.error("Download failed - check the logs for details")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()