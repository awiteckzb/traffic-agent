AGENT_RECOMMENDATION_PROMPT = """You are an expert traffic engineer. Analyze the following intersection scenario and provide optimal signal timing recommendations:
Intersection Type: {intersection_type}
Lanes:
{lanes}

Peak Traffic Volumes:
{peak_traffic}

Special Conditions: {special_conditions}
Time of Day: {time_of_day}

Please provide:
1. Optimal signal timing for each phase
2. Turn signal recommendations if needed
3. Complete cycle length
4. Priority phases
5. Detailed reasoning for your recommendations

Consider:
- Safety for all users
- Traffic flow efficiency
- Special condition impacts
- Peak volume handling
"""

PLANNING_PROMPT = {
    "system_message": """You are an expert traffic engineer focusing on signal timing optimization. Your expertise lies in:
    - Creating safe and efficient traffic flow patterns
    - Prioritizing safety while maintaining optimal throughput
    - Balancing competing needs of different road users
    - Considering both immediate and downstream effects of signal timing changes""",
    "user_template": """
    Given this traffic scenario, create a structured analysis plan. Your plan should:
    1. Identify key challenges (2-4 challenges, focus on critical issues that could impact safety or significantly affect flow)
    2. List main factors to analyze (3-5 factors, must include safety metrics and efficiency metrics)
    3. Propose analysis steps in order (4-6 steps, each step should build on previous steps)

    Format your response as JSON with the following structure:
    {{
        "challenges": [list of key challenges],
        "factors": [list of factors to analyze],
        "steps": [ordered list of analysis steps]
    }}

    Here is the scenario:
    {scenario}

    Your proposed plan:
    """,
    "select_best_plan_prompt": """You are an expert traffic engineer. You are given three plans for a traffic scenario and asked to select the best plan. Your selection should be based on the most effective use of resources (time and money) to achieve the best outcomes for the given scenario. This is the scenario:
    {scenario}

    Here are the three plans:
    {plans}

    Output the index of the best plan. For example, if plan 2 is the best, output "2".
    Your selection:
    """,
    "example_output": {
        "challenges": [
            "Heavy north-south traffic during peak hours creating long queues",
            "School proximity requiring extra pedestrian safety measures",
            "Unbalanced lane configuration affecting flow distribution",
        ],
        "factors": [
            "Peak hour volume ratios between approaches",
            "Pedestrian crossing frequencies and patterns",
            "Minimum green time requirements for safety",
            "Queue length predictions for each approach",
        ],
        "steps": [
            "Analyze peak hour traffic patterns and calculate volume-to-capacity ratios",
            "Determine minimum green times based on safety requirements and school schedule",
            "Calculate optimal cycle lengths for different periods",
            "Develop timing plans with specific phase splits and transition strategies",
        ],
    },
}


ANALYSIS_PROMPT = {
    "system_message": """You are an expert traffic engineer focusing on signal timing optimization. You must always provide:
    1. Specific phase timings for each direction (north-south and east-west at minimum)
    2. A complete cycle length that accounts for all phases
    3. Clear priority phases based on traffic patterns
    4. Turn signal timings when needed for safety or efficiency
    
    Your recommendations must follow standard traffic engineering principles:
    - Minimum green time of 15 seconds per phase
    - Maximum cycle length of 180 seconds
    - Phase timings must sum to the total cycle length
    - Higher-volume approaches should get proportionally more green time""",
    "user_template": """
    Based on this traffic scenario and analysis plan, provide detailed signal timing recommendations.

    SCENARIO:
    {scenario}

    ANALYSIS PLAN:
    {plan}

    Follow each step in the plan and provide your timing recommendations in the specified JSON format.
    Remember to address each challenge and factor listed in the plan.
    """,
    "example_output": {
        "phase_timings": {"north-south": 45, "east-west": 30},
        "turn_signal_timings": {"north": 15, "south": 15},
        "cycle_length": 90,
        "priority_phases": ["north-south"],
        "reasoning": "Detailed explanation of the timing decisions...",
    },
}
