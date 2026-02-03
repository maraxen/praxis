"""Browser stub for praxis.protocol.protocols.selective_transfer module.

This is the actual protocol module that cloudpickle references.
The function 'selective_transfer' is pickled and deserialized - we only
need the module to exist so cloudpickle can find it.
"""

def selective_transfer(*args, **kwargs):
    """Stub - actual function comes from pickle."""
    pass
