import os
import sys
import logging
import logging.handlers

# Sane defaults for the logging module
# Making logging.info and below actually do something by default
logging.root.level = 0
# Disable an unnecessary hack that obscures improper configuration
logging.lastResort = logging.Handler()
# Avoid implicit magic when using logging.* methods by doing it up front
logging.basicConfig()
# Fix syslog tag
logging.handlers.SysLogHandler.ident = f'itemtf[{os.getpid()}]: '

# Set up logger
# https://docs.python.org/3/howto/logging-cookbook.html#customized-exception-formatting
class OneLineExceptionFormatter(logging.Formatter):
    def formatException(self, exc_info):
        """
        Format an exception so that it prints on a single line.
        """
        result = super().formatException(exc_info)
        return repr(result)  # or format into one line however you want to

    def format(self, record):
        s = super().format(record)
        if record.exc_text:
            s = s.replace('\n', '') + '|'
        return s

logging.getLogger('blacksheep.server').disabled = True

logger = logging.getLogger('uvicorn.error')

if not __debug__:
    logging.getLogger('uvicorn.access').disabled = True
    for handler in logger.handlers:
        handler.formatter = OneLineExceptionFormatter()

sys.excepthook = (lambda type, value, traceback:
    logger.critical(value, exc_info=(type, value, traceback)))
