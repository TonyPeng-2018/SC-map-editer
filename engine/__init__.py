"""claude-scmap engine: read, understand and edit StarCraft (.scx/.scm) maps."""
from .scmap import SCMap
from .chk import CHK, StringTable
from .triggers import TriggerSection, Trigger, CONDITIONS, ACTIONS, player_name
from . import mpq

__all__ = [
    'SCMap', 'CHK', 'StringTable', 'TriggerSection', 'Trigger',
    'CONDITIONS', 'ACTIONS', 'player_name', 'mpq',
]
__version__ = '0.1.0'
