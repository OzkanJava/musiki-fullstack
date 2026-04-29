"""
Birebir port: seek-tune/server/models/models.go
"""
from dataclasses import dataclass


@dataclass
class Couple:
    anchor_time_ms: int  # uint32
    song_id: int         # uint32


@dataclass
class Peak:
    freq: float  # Hz
    time: float  # seconds
