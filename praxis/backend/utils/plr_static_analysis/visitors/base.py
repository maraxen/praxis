"""Base visitor utilities for PLR static analysis."""

import libcst as cst


class BasePLRVisitor(cst.CSTVisitor):
  """Base visitor with common utilities for PLR analysis."""

  def __init__(self, module_path: str, file_path: str) -> None:
    """Initialize the visitor.

    Args:
      module_path: The Python module path (e.g., 'pylabrobot.legacy.liquid_handling.backends.hamilton')
      file_path: The absolute file path to the source file

    """
    self.module_path = module_path
    self.file_path = file_path

  def _get_docstring(self, body: cst.BaseSuite) -> str | None:
    """Extract docstring from class/function body.

    Args:
      body: The body of a class or function definition.

    Returns:
      The docstring if found, None otherwise.

    """
    if isinstance(body, cst.IndentedBlock):
      if not body.body:
        return None
      first_stmt = body.body[0]
      if isinstance(first_stmt, cst.SimpleStatementLine) and first_stmt.body:
        first_expr = first_stmt.body[0]
        if isinstance(first_expr, cst.Expr):
          value = first_expr.value
          return self._extract_string_value(value)
    return None

  def _extract_string_value(self, node: cst.BaseExpression) -> str | None:
    """Extract string value from a string literal node.

    Args:
      node: A CST expression node.

    Returns:
      The string value if it's a string literal, None otherwise.

    """
    if isinstance(node, cst.SimpleString):
      # Remove quotes and handle raw/byte strings
      raw = node.value
      # Strip quote characters (single, double, triple)
      if raw.startswith(('"""', "'''")):
        return raw[3:-3]
      if raw.startswith(('"', "'")):
        return raw[1:-1]
      return raw
    if isinstance(node, cst.ConcatenatedString):
      # Handle concatenated strings
      parts = []
      for part in node.left, node.right:
        extracted = self._extract_string_value(part)
        if extracted:
          parts.append(extracted)
      return "".join(parts) if parts else None
    if isinstance(node, cst.FormattedString):
      # Can't evaluate f-strings statically
      return None
    return None

  def _is_abstract_class(self, node: cst.ClassDef) -> bool:
    """Check if class uses ABC metaclass or has abstract decorators.

    Args:
      node: A class definition node.

    Returns:
      True if the class is abstract.

    """
    # Check for ABC in bases or metaclass=ABCMeta
    for arg in node.bases:
      # Check direct ABC inheritance
      if isinstance(arg.value, cst.Name) and arg.value.value in ("ABC", "ABCMeta"):
        return True
      # Check metaclass=ABCMeta
      if (
        arg.keyword
        and isinstance(arg.keyword, cst.Name)
        and arg.keyword.value == "metaclass"
        and isinstance(arg.value, cst.Name)
        and arg.value.value == "ABCMeta"
      ):
        return True

    # Check for @abstractmethod decorators on methods (would need body traversal)
    # For now, we'll detect this in the capability extractor
    return False

  def _attribute_to_string(self, node: cst.Attribute) -> str:
    """Convert an Attribute node to a dotted string.

    Args:
      node: An Attribute node (e.g., module.ClassName)

    Returns:
      The dotted string representation.

    """
    parts = []
    current: cst.BaseExpression = node
    while isinstance(current, cst.Attribute):
      parts.append(current.attr.value)
      current = current.value
    if isinstance(current, cst.Name):
      parts.append(current.value)
    return ".".join(reversed(parts))

  def _name_to_string(self, node: cst.BaseExpression) -> str | None:
    """Convert a Name or Attribute node to a string.

    Args:
      node: A Name or Attribute node.

    Returns:
      The string representation, or None if not applicable.

    """
    if isinstance(node, cst.Name):
      return node.value
    if isinstance(node, cst.Attribute):
      return self._attribute_to_string(node)
    return None
