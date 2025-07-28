import os
import logging
from logging.handlers import TimedRotatingFileHandler


os.makedirs(name="logs", exist_ok=True)

# Обработчик ротации логов
log_handler = TimedRotatingFileHandler(
    filename='logs/log.txt',
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))


logger = logging.getLogger("main_logger")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
