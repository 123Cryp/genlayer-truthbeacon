"""
Shared test bootstrap.

Every test module in this package needs the same three things:
  1. The offline `genlayer` SDK stub (tests/genlayer_stub/) on
     sys.path, so contract.py's `from genlayer import *` resolves
     without a real GenLayer node.
  2. `contract.py` loaded as a module (it lives one directory up and
     is not itself part of the `tests` package).
  3. A `make_contract()` helper that returns a fresh, empty
     TruthBeacon instance for each test.

Centralizing this here means each test file just does:

    from tests._bootstrap import TruthBeacon, gl, make_contract

instead of repeating the sys.path / importlib wiring in every file -
one obvious place to look if this setup ever needs to change, and one
less thing for a reviewer to have to verify is consistent across
files.
"""

import importlib.util
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_STUB_DIR = os.path.join(_THIS_DIR, "genlayer_stub")
if _STUB_DIR not in sys.path:
    sys.path.insert(0, _STUB_DIR)

_CONTRACT_PATH = os.path.join(os.path.dirname(_THIS_DIR), "contract.py")

_spec = importlib.util.spec_from_file_location("truthbeacon_contract", _CONTRACT_PATH)
_contract_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract_module)

TruthBeacon = _contract_module.TruthBeacon
gl = _contract_module.gl


def make_contract() -> "TruthBeacon":
    """
    Return a fresh TruthBeacon instance with empty storage.

    `TruthBeacon()` alone is sufficient: the offline stub's
    `_Contract.__new__` pre-populates the TreeMap storage fields
    (mirroring how real GenVM persistent storage starts out empty
    without the contract having to initialize it by hand), and the
    normal Python constructor already calls `__init__` exactly once
    after `__new__` - there is no need to call `__init__` a second
    time here.
    """
    return TruthBeacon()
