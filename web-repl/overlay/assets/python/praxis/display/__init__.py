"""``praxis.display``: the notebook display layer (spec 260929_notebook-display-epic.md).

``install()`` turns it on in the kernel (the bootstrap's non-fatal stage, D13); ``RunLedger`` is the
explicit run recorder (D9); ``render(obj)`` returns the ``(data, metadata)`` mimebundle of a plate, tip
rack, deck or container, for tests and explicit use.

Plain CPython at import: no PyLabRobot, IPython or ``js`` is imported until something needs it.
"""

from .install import Installed, install, render
from .ledger import RunLedger

__all__ = ["Installed", "RunLedger", "install", "render"]
