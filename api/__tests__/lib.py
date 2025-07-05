from contextlib import contextmanager
from django.test.utils import CaptureQueriesContext
from django.db import connection, reset_queries

@contextmanager
def wrap_with_query_capture(reset=True, show_sql=False):
    if reset:
        reset_queries()
        
    with CaptureQueriesContext(connection) as ctx:
        yield ctx