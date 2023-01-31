import logging

class EventCreateFilter(logging.Filter):
     def filter(self, record):
         return record.is_create_event