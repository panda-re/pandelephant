import enum
import json
from typing import Dict

# Conveniences ---------------------------------------------------------------------------------------------------------

class PrintableEnum(enum.Enum):

    '''
    Enum display trait
    '''

    def __str__(self):
        return str(self.value)

class SyscallCategory(PrintableEnum):

    '''
    Functional systemcall category (non-exhaustive, just IGLOO-relevant)
    '''

    # File handling
    FILE_SETUP  = "FILE_SETUP"
    FILE_STATUS = "FILE_STATUS"
    FILE_IO     = "FILE_IO"

    # Network Interaction
    NET_SETUP   = "NET_SETUP"
    NET_IO      = "NET_IO"

    # Process Control
    PROC_LIFE   = "PROC_LIFE"
    PROC_IPC    = "PROC_IPC"

    # Hardware Interaction
    HW          = "HW"

    # Privilaged
    PRIV        = "PRIV"

    # None of the above
    OTHER       = "OTHER"

# Dynamic hashmap init (name -> category) ------------------------------------------------------------------------------

_cat_map_temp: Dict[str, str] = json.load(open('sys_cat.json'))
_cat_map_final: Dict[str, SyscallCategory] = {k: SyscallCategory[v.upper()] for (k, v) in _cat_map_temp.items()}

# Public API -----------------------------------------------------------------------------------------------------------

def syscall_name_to_category(name: str) -> SyscallCategory:

    '''
    Syscall name -> Syscall category enum
    '''

    # Python3.9: text.removeprefix(prefix)
    # Ubuntu 20.04 -> Python 3.8.5 :(
    def rm_prefix(text: str, prefix: str) -> str:
        if text.startswith(prefix):
            return text[len(prefix):]
        else:
            return text

    name = rm_prefix(name.lower(), "sys_")
    return _cat_map_final.get(name, SyscallCategory.OTHER)

