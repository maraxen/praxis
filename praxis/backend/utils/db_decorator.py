"""Database transaction decorator for handling session management."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar, cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.utils.errors import PraxisError

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def handle_db_transaction(func: F) -> F:
  """Manage database transactions in service layer methods.

  This decorator wraps an async function that may take a SQLAlchemy `AsyncSession`
  as an argument or be a method of a class that has an `_session` or `db` attribute.
  It ensures that the session is properly committed on success and rolled back on any exception.

  Args:
      func (Callable): The async function to be decorated.

  Returns:
      Callable: The wrapped async function with transaction management logic.

  Raises:
      Exception: Re-raises any exception that occurs within the decorated function
      after rolling back the transaction.

  """

  @wraps(func)
  async def wrapper(*args: Any, **kwargs: Any) -> Any:
    """Wrap the function with transaction handling.

    Args:
        *args: Positional arguments passed to the decorated function.
        **kwargs: Keyword arguments passed to the decorated function.

    Returns:
        The return value of the decorated function.

    Raises:
        Exception: Re-raises any exception from the decorated function.

    """
    db_session_arg_index = -1
    for i, arg in enumerate(args):
      if isinstance(arg, AsyncSession):
        db_session_arg_index = i
        break

    db: AsyncSession | None = None
    if db_session_arg_index != -1:
      db = args[db_session_arg_index]
    elif "db" in kwargs:
      db = kwargs["db"]
    elif len(args) > 0:
      # Check if self has a session (common in service classes)
      self_obj = args[0]
      if hasattr(self_obj, "_session") and isinstance(self_obj._session, AsyncSession):
        db = self_obj._session
      elif hasattr(self_obj, "db") and isinstance(self_obj.db, AsyncSession):
        db = self_obj.db

    if db is None:
      msg = (
        f"Function {func.__name__} decorated with @handle_db_transaction must have a 'db' argument "
        "or be a method of a class with an '_session' or 'db' attribute."
      )
      raise TypeError(msg)

    try:
      result = await func(*args, **kwargs)
      await db.commit()
      return result
    except IntegrityError as e:
      await db.rollback()
      msg = f"Database integrity error: {e.orig}" if hasattr(e, "orig") else str(e)
      raise ValueError(msg) from e
    except (ValueError, PraxisError):
      await db.rollback()
      raise
    except Exception as e:
      await db.rollback()
      msg = f"An unexpected error occurred: {e!s}"
      raise ValueError(msg) from e

  return cast("F", wrapper)
