from formatter import escape_dollar


def test_escape_dollar():
    cases = [
        {"input": "test", "expected": "test"},
        {"input": "$test", "expected": "$$test"},
        {"input": "$$test", "expected": "$$$$test"},
        {"input": "$$$test", "expected": "$$$$$$test"},
        {"input": "$test$", "expected": "$$test$$"},
    ]
    for case in cases:
        assert escape_dollar(case["input"]) == case["expected"]
