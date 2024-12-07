from pydantic import BaseModel
from typing import Dict, List, Optional


class Plan(BaseModel):
    challenges: List[str]
    factors: List[str]
    steps: List[str]


class TrafficScenario(BaseModel):
    """
    Represents a traffic intersection scenario
    """

    intersection_type: str  # e.g., "4-way", "3-way"
    lanes: Dict[str, int]  # e.g., {"north": 2, "south": 2, "east": 1, "west": 1}
    peak_traffic: Dict[str, float]  # Traffic volume by direction
    special_conditions: List[str]  # e.g., ["school_nearby", "heavy_pedestrian"]
    time_of_day: str  # e.g., "morning_rush", "midday", "evening_rush"


class SignalTiming(BaseModel):
    """Represents a signal timing recommendation"""

    phase_timings: Dict[str, int]  # e.g., {"north-south": 45, "east-west": 30}
    turn_signal_timings: Optional[Dict[str, int]] = None
    cycle_length: int
    priority_phases: List[str]
    reasoning: str


class PlanVerification(BaseModel):
    challenge_addressed: bool
    explanation: str
    confidence: float
