"""claude-scmap engine: read, understand and edit StarCraft (.scx/.scm) maps."""
from .scmap import SCMap
from .chk import CHK, StringTable
from .triggers import TriggerSection, Trigger, CONDITIONS, ACTIONS, player_name
from .triggerbuild import TriggerBuilder, C, A
from .units import UnitSection, unit_id, unit_name
from .terrain import Terrain
from . import mpq

__all__ = [
    'SCMap', 'CHK', 'StringTable', 'TriggerSection', 'Trigger',
    'CONDITIONS', 'ACTIONS', 'player_name', 'mpq',
    'TriggerBuilder', 'C', 'A', 'UnitSection', 'unit_id', 'unit_name', 'Terrain',
]
__version__ = '0.1.0'
