"""Browser stub for praxis.backend.core.decorators package."""
from .models import *

def protocol_function(*args, **kwargs):
    """Browser stub for protocol_function decorator.
    
    Returns a decorator that just returns the function as-is,
    since Pyodide handles execution differently.
    """
    def decorator(func):
        return func
    
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator

__all__ = [
    "protocol_function",
]
