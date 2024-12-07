# tests/test_traffic_agent.py
import pytest
from unittest.mock import Mock, patch
from agent.core.brain import (
    TrafficAgent,
    TrafficScenario,
    Plan,
    SignalTiming,
    PlanningError,
    AnalysisError,
)
from pydantic import ValidationError

# from pprint import pprint
import json


@pytest.fixture
def agent():
    return TrafficAgent()


@pytest.fixture
def sample_scenario():
    return TrafficScenario(
        intersection_type="4-way",
        lanes={"north": 2, "south": 2, "east": 1, "west": 1},
        peak_traffic={"north": 0.8, "south": 0.7, "east": 0.3, "west": 0.3},
        special_conditions=["school_nearby"],
        time_of_day="morning_rush",
    )


@pytest.fixture
def sample_plan():
    return Plan(
        challenges=[
            "Heavy north-south traffic during peak hours",
            "School nearby requiring special consideration",
        ],
        factors=[
            "Peak hour volume ratios",
            "Pedestrian safety requirements",
            "Minimum green time requirements",
        ],
        steps=[
            "Analyze peak traffic patterns",
            "Determine minimum green times",
            "Calculate optimal cycle length",
        ],
    )


# Unit Tests
class TestUnitComponents:
    def test_scenario_creation(self, sample_scenario):
        """Test if scenario is created correctly"""
        assert sample_scenario.intersection_type == "4-way"
        assert sample_scenario.lanes["north"] == 2
        assert "school_nearby" in sample_scenario.special_conditions

    def test_plan_creation(self, sample_plan):
        """Test if plan is created correctly"""
        assert len(sample_plan.challenges) == 2
        assert len(sample_plan.factors) == 3
        assert len(sample_plan.steps) == 3

    def test_format_scenario(self, agent, sample_scenario):
        """Test scenario formatting for prompts"""
        formatted = agent._format_scenario(sample_scenario)
        assert "4-way" in formatted
        assert "school_nearby" in formatted


# Integration Tests
class TestIntegration:
    @patch("openai.OpenAI")
    def test_plan_creation_integration(self, mock_openai, agent, sample_scenario):
        """Test plan creation with mocked OpenAI response"""
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(
                    function_call=Mock(
                        arguments='{"challenges": ["test"], "factors": ["test"], "steps": ["test"]}'
                    )
                )
            )
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        plan = agent._create_plan(sample_scenario)
        assert isinstance(plan, Plan)

    @patch("agent.core.brain.OpenAI")  # or whatever path we're using
    def test_analysis_integration(
        self, mock_openai, agent, sample_scenario, sample_plan
    ):
        print("\nDEBUG: Patch applied, mock_openai:", mock_openai)
        # Create a mock completion object
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(
                    function_call=Mock(
                        arguments=json.dumps(
                            {
                                "phase_timings": {"north-south": 60, "east-west": 40},
                                "cycle_length": 100,
                                "priority_phases": ["north-south"],
                                "reasoning": "Given the heavy north-south traffic flow...",
                            }
                        )
                    )
                )
            )
        ]

        # Configure the mock OpenAI client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        # Now when your code calls OpenAI, it will use this mock
        timing = agent.analyze_with_plan(sample_scenario, sample_plan)

        assert isinstance(timing, SignalTiming)
        assert timing.cycle_length == 100
        assert timing.phase_timings["north-south"] == 60


# End-to-End Tests
class TestEndToEnd:
    def test_full_workflow(self, agent, sample_scenario):
        """Test the entire workflow from scenario to timing recommendations"""
        try:
            timing = agent.analyze_scenario(sample_scenario)
            assert isinstance(timing, SignalTiming)
            assert timing.cycle_length > 0
            assert len(timing.phase_timings) > 0
            assert timing.reasoning is not None
        except (PlanningError, AnalysisError) as e:
            pytest.fail(f"Full workflow test failed: {str(e)}")

    def test_error_handling(self, agent):
        """Test error handling with invalid scenario"""
        with pytest.raises(ValidationError):
            invalid_scenario = TrafficScenario(
                intersection_type="invalid",
                lanes={},  # Invalid empty lanes
                peak_traffic={},
                special_conditions=[],
                time_of_day="invalid_time",
            )
            agent.analyze_scenario(invalid_scenario)


# Edge Cases and Stress Tests
class TestEdgeCases:
    @pytest.mark.parametrize(
        "special_condition",
        [
            ["emergency_route"],
            ["heavy_pedestrian"],
            ["construction_nearby"],
            ["multiple_schools"],
        ],
    )
    def test_various_conditions(self, agent, sample_scenario, special_condition):
        """Test handling of different special conditions"""
        scenario = sample_scenario.copy()
        scenario.special_conditions = special_condition
        timing = agent.analyze_scenario(scenario)
        assert special_condition[0] in timing.reasoning.lower()

    def test_high_traffic_scenario(self, agent):
        """Test handling of extreme traffic conditions"""
        scenario = TrafficScenario(
            intersection_type="4-way",
            lanes={"north": 3, "south": 3, "east": 3, "west": 3},
            peak_traffic={"north": 0.95, "south": 0.95, "east": 0.95, "west": 0.95},
            special_conditions=[],
            time_of_day="peak_rush",
        )
        timing = agent.analyze_scenario(scenario)
        assert timing.cycle_length >= 90  # Expect longer cycle for heavy traffic
