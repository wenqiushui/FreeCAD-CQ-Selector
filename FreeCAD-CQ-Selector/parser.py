import re

def parse_query(query_string: str) -> dict:
    """
    Parses a query string and returns a dictionary representing the parsed query.

    Args:
        query_string: The query string to parse.
                      Examples: "faces > Z", "edges < Y", "vertices | X", "faces # -X"

    Returns:
        A dictionary representing the parsed query.
        Examples:
            {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'}
            {'type': 'directional', 'entity': 'faces', 'direction': '-X'}

    Raises:
        ValueError: If the query string is invalid.
    """
    # Regular expression to capture positional and directional queries
    # It's a bit complex, so let's break it down:
    # ^(...)$ - Matches the entire string
    # (faces|edges|vertices) - Captures the entity type (group 1)
    # \s+ - Matches one or more spaces
    # (?: ... ) - Non-capturing group for the two types of queries
    # Positional query part:
    #   ([><|]) - Captures the operator (group 2 for positional)
    #   \s+ - Matches one or more spaces
    #   ([XYZ]) - Captures the axis (group 3 for positional)
    # Directional query part:
    #   (#) - Captures the '#' symbol (group 4 for directional)
    #   \s+ - Matches one or more spaces
    #   (-?[XYZ]) - Captures the direction (e.g., X, -Y) (group 5 for directional)
    query_pattern = re.compile(
        r"^(faces|edges|vertices)\s+(?:([><|])\s+([XYZ])|(#)\s+(-?[XYZ]))$"
    )

    match = query_pattern.match(query_string)

    if not match:
        raise ValueError(
            f"Invalid query string format: '{query_string}'. "
            "Supported formats: '[entity_type] [>|<|] [X|Y|Z]' or "
            "'faces # [X|Y|Z|-X|-Y|-Z]'"
        )

    entity_type = match.group(1)

    # Check if it's a positional query (groups 2 and 3 are populated)
    if match.group(2) and match.group(3):
        operator = match.group(2)
        axis = match.group(3)
        return {
            'type': 'positional',
            'entity': entity_type,
            'operator': operator,
            'axis': axis
        }
    # Check if it's a directional query (groups 4 and 5 are populated)
    elif match.group(4) and match.group(5):
        # Directional queries are only supported for 'faces'
        if entity_type != 'faces':
            raise ValueError(
                f"Invalid entity type for directional query: '{entity_type}'. "
                "Only 'faces' allowed for directional queries (e.g., 'faces # X')."
            )
        direction = match.group(5)
        return {
            'type': 'directional',
            'entity': entity_type,
            'direction': direction
        }
    else:
        # This case should ideally not be reached if the regex is correct
        # and the initial check `if not match:` works.
        # However, it's good practice to have a fallback.
        raise ValueError(
            f"Invalid query string structure after regex match: '{query_string}'. "
            "This indicates an unexpected parsing issue."
        )

if __name__ == '__main__':
    # Test cases
    queries_to_test = {
        "faces > Z": {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'},
        "edges < Y": {'type': 'positional', 'entity': 'edges', 'operator': '<', 'axis': 'Y'},
        "vertices | X": {'type': 'positional', 'entity': 'vertices', 'operator': '|', 'axis': 'X'},
        "faces # -X": {'type': 'directional', 'entity': 'faces', 'direction': '-X'},
        "faces # Y": {'type': 'directional', 'entity': 'faces', 'direction': 'Y'},
    }
    invalid_queries = [
        "face > Z",        # Invalid entity
        "edges & Y",       # Invalid operator
        "vertices | A",    # Invalid axis
        "faces # XX",      # Invalid direction
        "edges # X",       # Invalid entity for directional
        "faces > XX",      # Invalid axis for positional
        "faces #",         # Missing direction
        "vertices <",      # Missing axis
        "text < X",        # Invalid entity type
        "faces > Z extra", # Extra characters
        " faces > Z",      # Leading space
    ]

    print("--- Valid Queries ---")
    for q_str, expected in queries_to_test.items():
        try:
            result = parse_query(q_str)
            print(f"Query: '{q_str}' -> Parsed: {result} -> Correct: {result == expected}")
            if result != expected:
                print(f"  Mismatch! Expected: {expected}")
        except ValueError as e:
            print(f"Query: '{q_str}' -> Error: {e} (UNEXPECTED)")

    print("\n--- Invalid Queries (expecting ValueErrors) ---")
    for q_str in invalid_queries:
        try:
            result = parse_query(q_str)
            print(f"Query: '{q_str}' -> Parsed: {result} (UNEXPECTED - should have failed)")
        except ValueError as e:
            print(f"Query: '{q_str}' -> Error: {e} (EXPECTED)")

    # Example of a more specific invalid case for directional query
    print("\n--- Specific Invalid Directional Query ---")
    try:
        parse_query("edges # Z")
        print("Query: 'edges # Z' -> Parsed (UNEXPECTED)")
    except ValueError as e:
        print(f"Query: 'edges # Z' -> Error: {e} (EXPECTED)")

    try:
        parse_query("vertices # -Y")
        print("Query: 'vertices # -Y' -> Parsed (UNEXPECTED)")
    except ValueError as e:
        print(f"Query: 'vertices # -Y' -> Error: {e} (EXPECTED)")

    print("\n--- Testing regex directly for debugging ---")
    query_pattern_debug = re.compile(
        r"^(faces|edges|vertices)\s+(?:([><|])\s+([XYZ])|(#)\s+(-?[XYZ]))$"
    )
    test_strings_debug = [
        "faces > Z", "edges < Y", "vertices | X", "faces # -X", "faces # Y",
        "edges # Z" # this should match the overall pattern but fail validation later
    ]
    for ts in test_strings_debug:
        match = query_pattern_debug.match(ts)
        if match:
            print(f"String: '{ts}' -> Groups: {match.groups()}")
        else:
            print(f"String: '{ts}' -> No match")

    # Test case for the error message if entity is not 'faces' for directional query
    try:
        parse_query("edges # X")
    except ValueError as e:
        if "Only 'faces' allowed for directional queries" in str(e):
            print("Correctly caught error for 'edges # X'")
        else:
            print(f"Unexpected error for 'edges # X': {e}")

    # Test case for query with extra parts
    try:
        parse_query("faces > Z and something else")
    except ValueError as e:
        if "Invalid query string format" in str(e):
            print("Correctly caught error for 'faces > Z and something else'")
        else:
            print(f"Unexpected error for 'faces > Z and something else': {e}")

    # Test case for query with only entity
    try:
        parse_query("faces")
    except ValueError as e:
        if "Invalid query string format" in str(e):
            print("Correctly caught error for 'faces'")
        else:
            print(f"Unexpected error for 'faces': {e}")

    # Test case for query with entity and operator but no axis/direction
    try:
        parse_query("faces >")
    except ValueError as e:
        if "Invalid query string format" in str(e):
            print("Correctly caught error for 'faces >'")
        else:
            print(f"Unexpected error for 'faces >': {e}")

    print("Parser implementation complete with basic tests.")
