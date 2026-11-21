"""burr-solver : identification et résolution de casse-têtes burr à 6 pièces (2x2x8)."""
from .assembly import assemble, unique_assemblies
from .disassembly import compress, disassemble
from .io import load_pieces

__version__ = "0.1.0"
__all__ = ["load_pieces", "assemble", "unique_assemblies", "disassemble", "compress"]
