"""Exercise IPython's real traceback formatter while Sciunit is recording."""
import sys
from IPython import get_ipython


def warm_traceback_formatter():
    try:
        raise RuntimeError('FLINC traceback dependency warmup')
    except RuntimeError:
        # Build and discard the formatted result; nothing is displayed or raised.
        get_ipython().InteractiveTB.structured_traceback(*sys.exc_info())


warm_traceback_formatter()
