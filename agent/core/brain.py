from typing import Dict, List
from openai import OpenAI
import os
from dotenv import load_dotenv
from agent.data.prompts import *
from agent.models.models import *
from tenacity import retry, stop_after_attempt, wait_exponential
import json
from pydantic import ValidationError
from pprint import pprint


from agent.core.knowledge_base import TrafficKnowledgeBase
from agent.exceptions.exceptions import PlanningError, AnalysisError
from agent.tools.tools import (
    create_traffic_plan,
    select_best_plan,
    create_signal_timing,
    verify_plan_coverage,
)


load_dotenv()


class TrafficAgent:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.context_history = []

    def _generate_prompt(self, scenario: TrafficScenario) -> str:
        """Generate a detailed prompt for the LLM"""
        prompt = AGENT_RECOMMENDATION_PROMPT.format(
            intersection_type=scenario.intersection_type,
            lanes=self._format_dict(scenario.lanes),
            peak_traffic=self._format_dict(scenario.peak_traffic),
            special_conditions=", ".join(scenario.special_conditions),
            time_of_day=scenario.time_of_day,
        )
        return prompt

    def _generate_plan_prompt(self, scenario: TrafficScenario) -> str:
        """Generate a prompt for the plan creation"""
        formatted_scenario = self._format_scenario(scenario)
        prompt = PLANNING_PROMPT["user_template"].format(scenario=formatted_scenario)
        return prompt

    def _format_scenario(self, scenario: TrafficScenario) -> str:
        """Format the scenario for the prompt"""
        return f"Intersection Type: {scenario.intersection_type}\nLanes: {self._format_dict(scenario.lanes)}\nPeak Traffic Volumes: {self._format_dict(scenario.peak_traffic)}\nSpecial Conditions: {', '.join(scenario.special_conditions)}\nTime of Day: {scenario.time_of_day}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _create_single_plan(self, scenario: TrafficScenario) -> Plan:
        """Create a single plan with error handling and function calling"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PLANNING_PROMPT["system_message"]},
                    {"role": "user", "content": self._generate_plan_prompt(scenario)},
                ],
                functions=[create_traffic_plan],
                function_call={"name": create_traffic_plan["name"]},
            )

            # Parse the function call response
            function_args = json.loads(
                response.choices[0].message.function_call.arguments
            )
            return Plan(**function_args)

        except json.JSONDecodeError as e:
            raise PlanningError(f"Failed to parse LLM response: {e}")
        except ValidationError as e:
            raise PlanningError(f"Invalid plan structure: {e}")
        except Exception as e:
            raise PlanningError(f"Unexpected error in plan creation: {e}")

    def _create_plan(self, scenario: TrafficScenario) -> Plan:
        """Create and select the best plan from multiple attempts"""
        try:
            # Generate three plans
            plans = []
            for _ in range(3):
                plan = self._create_single_plan(scenario)
                plans.append(plan)

            # Select the best plan
            best_plan = self._select_best_plan(plans, scenario)
            return best_plan

        except PlanningError as e:
            # If we have at least one valid plan, use it instead of failing
            if plans:
                return plans[0]
            raise PlanningError("Failed to create any valid plans")

    def _select_best_plan(self, plans: List[str], scenario: TrafficScenario) -> str:
        """Select the best plan using function calling for strict output"""
        try:
            plans_str = "\n\n".join(
                [
                    f"Plan {i+1}:\n" + plan.model_dump_json(indent=2)
                    for i, plan in enumerate(plans)
                ]
            )
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": PLANNING_PROMPT["select_best_plan_prompt"].format(
                            scenario=self._format_scenario(scenario), plans=plans_str
                        ),
                    }
                ],
                functions=[select_best_plan],
                function_call={"name": select_best_plan["name"]},
            )
            selection = json.loads(response.choices[0].message.function_call.arguments)
            index = selection["selected_index"]

            # Validate index
            if not 0 <= index < len(plans):
                raise PlanningError(f"Invalid plan index: {index}")

            return plans[index]

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            # If selection fails, return the first plan
            return plans[0]
        except Exception as e:
            raise PlanningError(f"Error in plan selection: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def analyze_with_plan(self, scenario: TrafficScenario, plan: Plan) -> SignalTiming:
        """Analyze a traffic scenario with a given plan"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT["system_message"]},
                    {
                        "role": "user",
                        "content": ANALYSIS_PROMPT["user_template"].format(
                            scenario=self._format_scenario(scenario),
                            plan=plan.model_dump_json(indent=2),
                        ),
                    },
                ],
                functions=[create_signal_timing],
                function_call={"name": create_signal_timing["name"]},
            )

            # print("\n=== Mock Response ===")
            # pprint(response.choices[0].message.function_call.arguments)

            function_args = json.loads(
                response.choices[0].message.function_call.arguments
            )

            # print("\n=== Parsed Arguments ===")
            # pprint(function_args)
            print("\n=== DEBUG ===")
            print("Type of function_args:", type(function_args))
            print("Keys in function_args:", function_args.keys())
            print("Full function_args:")
            pprint(function_args)
            print("=============\n")

            # Validate completeness and correctness
            self._validate_timing_logic(function_args, scenario)

            # Validate the recommendations
            timing = self._validate_timing_recommendations(function_args, plan)

            return timing

        except json.JSONDecodeError as e:
            raise AnalysisError(f"Failed to parse LLM response: {e}")
        except ValidationError as e:
            raise AnalysisError(f"Invalid timing structure: {e}")
        except Exception as e:
            raise AnalysisError(f"Unexpected error in analysis: {e}")

    def _validate_timing_logic(
        self, timing_dict: Dict, scenario: TrafficScenario
    ) -> None:
        """Validate that the timing recommendations make logical sense"""

        # Check that phase timings exist and cover all directions
        if "phase_timings" not in timing_dict:
            raise AnalysisError("No phase timings provided")

        phase_timings = timing_dict["phase_timings"]
        if not {"north-south", "east-west"}.issubset(phase_timings.keys()):
            raise AnalysisError("Missing required phase timings for main directions")

        # Validate cycle length matches phase timings
        total_phase_time = sum(phase_timings.values())
        if total_phase_time != timing_dict["cycle_length"]:
            raise AnalysisError(
                f"Cycle length ({timing_dict['cycle_length']}) doesn't match sum of phase timings ({total_phase_time})"
            )

        # Check that busier approaches get more green time
        ns_volume = max(
            scenario.peak_traffic.get("north", 0), scenario.peak_traffic.get("south", 0)
        )
        ew_volume = max(
            scenario.peak_traffic.get("east", 0), scenario.peak_traffic.get("west", 0)
        )
        if (
            ns_volume > ew_volume
            and phase_timings["north-south"] <= phase_timings["east-west"]
        ):
            raise AnalysisError(
                "Phase timings don't properly account for traffic volumes"
            )

        # Validate minimum and maximum timings
        for direction, time in phase_timings.items():
            if time < 15:
                raise AnalysisError(
                    f"Phase timing for {direction} is below minimum safe time"
                )

        if timing_dict["cycle_length"] > 180:
            raise AnalysisError("Cycle length exceeds maximum recommended duration")

    def _validate_timing_recommendations(
        self, timing_dict: Dict, plan: Plan
    ) -> SignalTiming:
        """Validate the timing recommendations"""
        timing = SignalTiming(**timing_dict)

        self._check_minimum_timings(timing)
        self._verify_plan_addressed(timing, plan)

        return timing

    def _check_minimum_timings(self, timing: SignalTiming):
        """Check that all timings meet minimum safety requirements"""
        for phase, time in timing.phase_timings.items():
            if time < 15:  # Example minimum green time
                raise AnalysisError(
                    f"Phase {phase} timing too short: minimum 15 seconds required"
                )

        if (
            timing.cycle_length < 60 or timing.cycle_length > 180
        ):  # Standard cycle length bounds
            raise AnalysisError(
                f"Cycle length {timing.cycle_length} outside acceptable range (60-180 seconds)"
            )

    def _verify_plan_addressed(self, timing: SignalTiming, plan: Plan) -> None:
        """
        Verify that the timing recommendations address all aspects of the plan
        using LLM to evaluate comprehensiveness and correctness
        """
        verification_prompt = {
            "role": "user",
            "content": f"""
            Analyze whether these signal timing recommendations properly address the analysis plan.
            
            PLAN:
            Challenges: {plan.challenges}
            Factors: {plan.factors}
            Steps: {plan.steps}

            TIMING RECOMMENDATIONS:
            Phase Timings: {timing.phase_timings}
            Turn Signal Timings: {timing.turn_signal_timings if timing.turn_signal_timings else 'None'}
            Cycle Length: {timing.cycle_length}
            Priority Phases: {timing.priority_phases}
            Reasoning: {timing.reasoning}
            """,
        }

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a traffic engineering expert verifying signal timing recommendations.",
                    },
                    verification_prompt,
                ],
                functions=[verify_plan_coverage],
                function_call={"name": verify_plan_coverage["name"]},
            )

            # Parse the verification results
            results = json.loads(response.choices[0].message.function_call.arguments)

            # Check if any critical elements were missed
            critical_misses = [
                v
                for v in results["verifications"]
                if not v["is_addressed"] and v["confidence"] > 0.8
            ]

            # If there are critical misses or the overall assessment is insufficient
            if critical_misses or not results["overall_assessment"]["is_sufficient"]:
                missing = results["overall_assessment"]["missing_elements"]
                recommendations = results["overall_assessment"]["recommendations"]

                raise AnalysisError(
                    f"Timing recommendations incomplete.\n"
                    f"Missing elements: {', '.join(missing)}\n"
                    f"Recommendations: {recommendations}"
                )

            # Store verification results for potential later use
            self.last_verification = results

        except Exception as e:
            raise AnalysisError(f"Error in plan verification: {str(e)}")

    # Update the main analyze_scenario method to use the new planning and analysis
    def analyze_scenario(self, scenario: TrafficScenario) -> SignalTiming:
        """Analyze a traffic scenario and provide signal timing recommendations"""
        try:
            # Create and select the best plan
            plan = self._create_plan(scenario)

            # Generate recommendations based on the plan
            timing = self.analyze_with_plan(scenario, plan)

            return timing

        except (PlanningError, AnalysisError) as e:
            # Log the error and try a simplified analysis as fallback
            print(f"Error in full analysis: {e}")
            return self._fallback_analysis(scenario)

    def _fallback_analysis(self, scenario: TrafficScenario) -> SignalTiming:
        """Simplified analysis when the full process fails"""
        # Implementation of a simpler, more robust analysis method
        # Could use simpler prompts and fewer validation steps
        # This would be a good place to add later for additional robustness
        raise NotImplementedError("Fallback analysis not implemented yet")

    def explain_recommendation(self, timing: SignalTiming) -> str:
        """Provide a detailed explanation of the timing recommendation"""
        return timing.reasoning

    def _format_dict(self, d: Dict) -> str:
        return "\n".join([f"- {k}: {v}" for k, v in d.items()])
