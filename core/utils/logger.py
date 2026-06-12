# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import sys


class ACTFormatter(logging.Formatter):
    """Custom log formatter for ACT with colored output.

    Provides color-coded log messages based on severity level.
    """

    # Color escape codes
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    green = "\033[92m"
    cyan = "\033[96m"
    red = "\x1b[31;20m"
    bold_white = "\033[1m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    # Format strings for log levels
    prefix = "[%(module)24s - "
    postfix = " %(message)s"
    level_formats = {
        logging.DEBUG: prefix + f"{green}%(levelname)s{reset}]" + postfix,
        logging.INFO: prefix + f"{bold_white}%(levelname)s{reset}]" + postfix,
        logging.WARNING: prefix + f"{yellow}%(levelname)s{reset}]" + postfix,
        logging.ERROR: prefix + f"{red}%(levelname)s{reset}]" + postfix,
        logging.CRITICAL: prefix + f"{bold_red}%(levelname)s{reset}]" + postfix,
    }

    def format(self, record):
        """Format a log record with appropriate color coding.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: Formatted log message with color codes.
        """
        level_format = self.level_formats.get(record.levelno)
        formatter = logging.Formatter(level_format)
        return formatter.format(record)


def clear_handlers():
    """Remove all non-StreamHandler handlers from the ACT logger."""
    for h in logging.getLogger("ACT").handlers:
        # don't remove the streamhandler to stdout (there are problems if it's
        # removed and re-added later)
        if isinstance(h, logging.StreamHandler):
            continue
        # remove any other handlers
        else:
            logging.getLogger("ACT").removeHandler(h)
            h.close()


def setup_logger(file_name=None, loglevel=None):
    """Set up the ACT logger with optional file output.

    Args:
        file_name (str): Optional path to log file.
        loglevel (int): Optional logging level (e.g., logging.DEBUG).
    """
    # Create ACT logger ... disambiguate from global root logger
    logger = logging.getLogger("ACT")
    logger.propagate = False  # prevent duplicate output
    if loglevel is not None:
        logger.setLevel(loglevel)

    # Formatter to be associated with all output handlers
    formatter = ACTFormatter()

    # Add handlers (log output destinations)
    new_handlers = []
    # Insert a streamhandler to stdout, if one doesn't exist already
    #   (we want at most 1 handler to stdout)
    current_handlers = logging.getLogger("ACT").handlers
    if not any([isinstance(h, logging.StreamHandler) for h in current_handlers]):
        new_handlers.append(logging.StreamHandler(sys.stdout))
    # Add any handlers to log files
    if file_name is not None:
        new_handlers.append(logging.FileHandler(file_name, "w", "utf-8"))
    # Apply ACT formatting
    for h in new_handlers:
        h.setFormatter(formatter)
        logger.addHandler(h)


log = logging.getLogger("ACT")
