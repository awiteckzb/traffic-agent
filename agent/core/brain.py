from typing import Dict, List, Optional
from openai import OpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from data.prompts import *
from models.models import *
from core.knowledge_base import TrafficKnowledgeBase

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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

    def _create_plan(self, scenario: TrafficScenario) -> str:
        """Create a plan for the scenario"""
        prompt = self._generate_plan_prompt(scenario)

        # Get three different plans from the LLM
        plans = []
        for _ in range(3):
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": PLANNING_PROMPT["system_message"]},
                    {"role": "user", "content": prompt},
                ],
            )
            plans.append(response.choices[0].message.content)

        # Select the best plan
        best_plan = self._select_best_plan(plans)
        return best_plan

    def _select_best_plan(self, plans: List[str], scenario: TrafficScenario) -> str:
        """Select the best plan from the list of plans"""
        prompt = PLANNING_PROMPT["select_best_plan_prompt"].format(
            scenario=self._format_scenario(scenario), plans=plans
        )
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        index = int(response.choices[0].message.content)
        return plans[index]

    def _format_dict(self, d: Dict) -> str:
        return "\n".join([f"- {k}: {v}" for k, v in d.items()])

    def analyze_scenario(self, scenario: TrafficScenario) -> SignalTiming:
        """Analyze a traffic scenario and provide signal timing recommendations"""
        prompt = self._generate_prompt(scenario)

        # Get recommendation from OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4 for better reasoning
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert traffic engineer focusing on signal timing optimization.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        # Parse the response and convert to SignalTiming
        # (We'll implement response parsing logic later)
        raw_response = response.choices[0].message.content
        timing = self._parse_recommendation(raw_response)

        # Store in context history
        self.context_history.append({"scenario": scenario, "recommendation": timing})

        return timing

    def _parse_recommendation(self, raw_response: str) -> SignalTiming:
        """
        Parse the LLM response into a structured SignalTiming object.
        This is a placeholder implementation - we'll make it more robust later.
        """
        # TODO: Implement proper parsing logic
        # Use mock data for now
        return SignalTiming(
            phase_timings={"north-south": 45, "east-west": 30},
            turn_signal_timings={"north": 15, "south": 15},
            cycle_length=90,
            priority_phases=["north-south"],
            reasoning=raw_response,
        )

    def explain_recommendation(self, timing: SignalTiming) -> str:
        """Provide a detailed explanation of the timing recommendation"""
        return timing.reasoning
