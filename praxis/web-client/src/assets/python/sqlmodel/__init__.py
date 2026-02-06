"""Browser-compatible stub for sqlmodel package.

SQLModel is a library that combines SQLAlchemy and Pydantic. In the browser
environment, we don't need SQLAlchemy ORM features, but we DO need Pydantic's
BaseModel for cloudpickle compatibility.

This stub provides SQLModel as an alias for pydantic.BaseModel, enabling
cloudpickle to deserialize protocol functions that use SQLModel classes.
"""

from pydantic import BaseModel

# SQLModel is essentially Pydantic BaseModel with SQLAlchemy table support.
# For browser execution, we only need the Pydantic part.
class SQLModel(BaseModel):
    """Browser stub for SQLModel - extends Pydantic BaseModel."""
    
    class Config:
        # Allow arbitrary types for flexibility with complex parameters
        arbitrary_types_allowed = True
        # Don't validate on assignment for stub compatibility
        validate_assignment = False

# Re-export Field from pydantic for convenience
try:
    from pydantic import Field
except ImportError:
    # Fallback if Field is not directly importable
    def Field(*args, **kwargs):
        """Stub for SQLModel Field."""
        return None

# Re-export Relationship as a stub
def Relationship(*args, **kwargs):
    """Stub for SQLModel Relationship - not needed in browser."""
    return None

__all__ = ['SQLModel', 'Field', 'Relationship']
