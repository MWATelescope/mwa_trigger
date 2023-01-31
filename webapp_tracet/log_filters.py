import logging

class EventCreateFilter(logging.Filter):
     def filter(self, record):
            return True