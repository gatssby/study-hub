"""Gunicorn lifecycle/error events without request targets or exception text."""
import logging
from gunicorn.glogging import Logger


class EventOnly(logging.Filter):
    def filter(self, record):
        record.msg = 'study_hub_observer runtime_event'
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


class SanitizedLogger(Logger):
    def setup(self, cfg):
        super().setup(cfg)
        self.error_log.addFilter(EventOnly())
        self.access_log.addFilter(EventOnly())
