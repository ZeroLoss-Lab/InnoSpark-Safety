from egs import EducationalGuardrailSystem

# 1. Configuration
# Note: The system will warn and skip modules if specific paths (e.g., knowledge_base) are not found.
CONFIG = {
    "model_front": "./models/front_model",
    "model_post": "./models/post_model",
    "blacklist_severe": "./data/severe_toxicity_keywords.json",
    "blacklist_moderate": "./data/moderate_toxicity_keywords.json",
    "knowledge_base": "./data/edu_knowledge_base"
}

print("\n" + "="*60)
print("Initializing Educational Guardrail System...")
print("="*60)

try:
    guardrail = EducationalGuardrailSystem(
        model_path_front=CONFIG["model_front"],
        model_path_post=CONFIG["model_post"],
        blacklist_path_severe=CONFIG["blacklist_severe"],
        blacklist_path_moderate=CONFIG["blacklist_moderate"],
        knowledge_base_dir=CONFIG["knowledge_base"]
    )
    print("\nSystem initialized successfully.")

except Exception as e:
    print(f"\nCRITICAL ERROR during initialization: {e}")
    exit(1)

# 2. Define Test Cases
test_cases = [
    {
        "id": 1,
        "desc": "Placeholder keyword check",
        "q": "example_term_alpha",
        "a": "This is a placeholder answer.",
        "expected": "safe"
    },
    {
        "id": 2,
        "desc": "Standard Educational Query",
        "q": "Can you explain photosynthesis?",
        "a": "Photosynthesis converts light energy into chemical energy in plants.",
        "expected": "safe"
    },
    {
        "id": 3,
        "desc": "Response audit placeholder",
        "q": "What is a summary?",
        "a": "placeholder_content_alpha",
        "expected": "safe"
    }
]

# 3. Run Batch Evaluation
print("\n" + "="*60)
print(f"Starting Batch Evaluation ({len(test_cases)} cases)...")
print("="*60)

for case in test_cases:
    print(f"\n🔹 [Case {case['id']}] {case['desc']}")
    print(f"   Q: {case['q']}")
    print(f"   A: {case['a']}")
    
    # Execute Evaluation
    result = guardrail.eval_EGS(case['q'], case['a'])
    
    # Print Results
    status_icon = "✅" if result == "safe" else "🚫"
    match_expected = " (Matches Expected)" if result == case['expected'] else f" (Expected: {case['expected']})"
    
    print(f"   👉 Final Result: {status_icon} {result.upper()}{match_expected}")
    print("   " + "-"*40)

print("\nDone.")
