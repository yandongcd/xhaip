"""Debate module — multi-agent consensus via structured declaration debate.

Phase 2 of xhaip intelligence upgrade. Implements:
- DeclarationLayer: LLM extracts verifiable facts from agent outputs
- ConflictDetector: deterministic comparison of declarations
- Moderator: dual LLM judge with appeal mechanism
- DebateEngine: orchestrates the debate flow
- DebateProtocol: context formatting for debate rounds
"""

from haip.debate.conflict import Conflict, ConflictDetector
from haip.debate.declaration import Declaration, DeclarationLayer
from haip.debate.engine import DebateContext, DebateEngine
from haip.debate.moderator import Moderator, ModeratorVote
from haip.debate.protocol import DebateProtocol

__all__ = [
    "Conflict",
    "ConflictDetector",
    "DebateContext",
    "DebateEngine",
    "DebateProtocol",
    "Declaration",
    "DeclarationLayer",
    "Moderator",
    "ModeratorVote",
]
