create_traffic_plan = {
    "name": "create_traffic_plan",
    "description": "Create a structured traffic analysis plan",
    "parameters": {
        "type": "object",
        "properties": {
            "challenges": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 2-4 key challenges",
            },
            "factors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 3-5 main factors to analyze",
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 4-6 ordered analysis steps",
            },
        },
        "required": ["challenges", "factors", "steps"],
    },
}

select_best_plan = {
    "name": "select_plan",
    "description": "Select the best plan index",
    "parameters": {
        "type": "object",
        "properties": {
            "selected_index": {
                "type": "integer",
                "description": "Index of the best plan (0-2)",
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation for the selection",
            },
        },
        "required": ["selected_index", "reasoning"],
    },
}

create_signal_timing = {
    "name": "create_signal_timing",
    "description": "Create signal timing recommendations",
    "parameters": {
        "type": "object",
        "properties": {
            "phase_timings": {
                "type": "object",
                "description": "Timing in seconds for each phase",
                "additionalProperties": {"type": "integer"},
            },
            "turn_signal_timings": {
                "type": "object",
                "description": "Optional timing in seconds for turn signals",
                "additionalProperties": {"type": "integer"},
            },
            "cycle_length": {
                "type": "integer",
                "description": "Total cycle length in seconds",
            },
            "priority_phases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of priority phases",
            },
            "reasoning": {
                "type": "string",
                "description": "Detailed explanation of timing decisions",
            },
        },
        "required": ["phase_timings", "cycle_length", "priority_phases", "reasoning"],
    },
}

verify_plan_coverage = {
    "name": "verify_plan_coverage",
    "description": "Verify how well the timing recommendations address each plan element",
    "parameters": {
        "type": "object",
        "properties": {
            "verifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "element": {"type": "string"},
                        "element_type": {
                            "type": "string",
                            "enum": ["challenge", "factor", "step"],
                        },
                        "is_addressed": {"type": "boolean"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "element",
                        "element_type",
                        "is_addressed",
                        "confidence",
                        "explanation",
                    ],
                },
            },
            "overall_assessment": {
                "type": "object",
                "properties": {
                    "is_sufficient": {"type": "boolean"},
                    "missing_elements": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "string"},
                },
                "required": ["is_sufficient", "missing_elements", "recommendations"],
            },
        },
        "required": ["verifications", "overall_assessment"],
    },
}
