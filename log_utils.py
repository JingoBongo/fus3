import logging
from logging.handlers import RotatingFileHandler

# Set up the logger
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'default.log'  # Ensure the daemon has permissions to write here

# Rotating file handler to keep logs manageable
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)  # 10MB per file, 5 backups
handler.setFormatter(log_formatter)

# Configure the logger
logger = logging.getLogger('Fus3')
logger.setLevel(logging.DEBUG)  # Set to DEBUG for more verbosity
logger.addHandler(handler)
