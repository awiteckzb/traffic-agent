from typing import Dict, List


class TrafficKnowledgeBase:
    """Storage for traffic engineering rules and best practices"""

    @staticmethod
    def get_minimum_green_time(intersection_type: str) -> int:
        """Get minimum green time based on intersection type"""
        minimums = {"4-way": 30, "3-way": 25, "t-junction": 25}
        return minimums.get(intersection_type, 30)

    @staticmethod
    def get_safety_guidelines(conditions: List[str]) -> Dict[str, str]:
        """Get safety guidelines based on conditions"""
        guidelines = {
            "school_nearby": "Minimum pedestrian crossing time of 25 seconds",
            "heavy_pedestrian": "Consider exclusive pedestrian phase",
            "emergency_route": "Provide emergency vehicle preemption",
        }
        return {cond: guidelines[cond] for cond in conditions if cond in guidelines}
