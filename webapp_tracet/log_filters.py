from contextvars import ContextVar
import logging

ctx_url = ContextVar('url', default={'path': 'None'})

class EventCreateFilter(logging.Filter):
     def filter(self, record):
          if (hasattr(record, 'event_create') and record.event_create):
               ctx_url.set('/event_create/')
          if (hasattr(record, 'event_create_finished') and record.event_create_finished):
               ctx_url.set(None)
               return True
          if (ctx_url.get() == '/event_create/'):
               record.url = ctx_url.get()
               return True