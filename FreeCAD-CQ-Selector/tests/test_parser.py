import sys
import os
import unittest

# Add the project root directory (parent of 'FreeCAD-CQ-Selector') to sys.path
# This allows imports like 'from FreeCAD_CQ_Selector.parser import parse_query'
PACKAGE_PARENT = '../..' # Go up two levels: tests -> FreeCAD-CQ-Selector -> project_root
# Make __file__ absolute before getting its directory
ABS_FILE_PATH = os.path.abspath(os.path.expanduser(__file__))
SCRIPT_DIR = os.path.dirname(ABS_FILE_PATH)
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT))
sys.path.insert(0, PROJECT_ROOT) # Insert at beginning to ensure priority

import importlib
parser_module = importlib.import_module("FreeCAD-CQ-Selector.parser")
parse_query = parser_module.parse_query

class TestQueryParser(unittest.TestCase):

    def test_valid_positional_queries(self):
        queries = {
            "faces > Z": {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'},
            "edges < X": {'type': 'positional', 'entity': 'edges', 'operator': '<', 'axis': 'X'},
            "vertices | Y": {'type': 'positional', 'entity': 'vertices', 'operator': '|', 'axis': 'Y'},
            "faces > X": {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'X'},
            "edges < Y": {'type': 'positional', 'entity': 'edges', 'operator': '<', 'axis': 'Y'},
            "vertices | Z": {'type': 'positional', 'entity': 'vertices', 'operator': '|', 'axis': 'Z'},
        }
        for q_str, expected in queries.items():
            with self.subTest(query=q_str):
                self.assertEqual(parse_query(q_str), expected)

    def test_valid_directional_queries(self):
        queries = {
            "faces # Z": {'type': 'directional', 'entity': 'faces', 'direction': 'Z'},
            "faces # -X": {'type': 'directional', 'entity': 'faces', 'direction': '-X'},
            "faces # Y": {'type': 'directional', 'entity': 'faces', 'direction': 'Y'},
            "faces # -Z": {'type': 'directional', 'entity': 'faces', 'direction': '-Z'},
        }
        for q_str, expected in queries.items():
            with self.subTest(query=q_str):
                self.assertEqual(parse_query(q_str), expected)

    def test_invalid_queries_raise_valueerror(self):
        invalid_queries = [
            "face > Z",        # Invalid entity type (singular)
            "shapes > Z",      # Unknown entity type
            "edges & Y",       # Invalid operator
            "vertices | A",    # Invalid axis
            "faces # XX",      # Invalid direction (too long)
            "faces # -A",      # Invalid direction (axis)
            "edges # X",       # Invalid entity for directional query
            "vertices # Y",    # Invalid entity for directional query
            "faces > XY",      # Invalid axis for positional
            "faces #",         # Missing direction
            "vertices <",      # Missing axis
            "text < X",        # Invalid entity type
            "faces > Z extra", # Extra characters at the end
            " faces > Z",      # Leading space (parser currently strict about no leading/trailing spaces)
            "faces > Z ",      # Trailing space
            # "faces  >  Z",  # This is now valid due to \s+ in regex, tested in test_edge_cases_spacing
            "",                # Empty query
            "faces>Z",         # No space around operator
        ]
        for q_str in invalid_queries:
            with self.subTest(query=q_str):
                with self.assertRaises(ValueError):
                    parse_query(q_str)

    def test_edge_cases_spacing(self):
        # Test queries that should be valid despite some spacing variations if parser becomes more flexible.
        # For now, the parser is strict as per its regex. If it's updated, these tests might change.
        # self.assertEqual(parse_query("faces  >  Z"), {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'})

        # Current parser is strict about single spaces based on \s+ in regex.
        # These will fail if the regex isn't `r"^(faces|edges|vertices)\s+([><|])\s+([XYZ])$"` etc.
        # and allows for multiple spaces. The current regex implies it handles multiple spaces.
        # Let's test one that should pass with current regex:
        self.assertEqual(parse_query("faces   >   Z"), {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'})
        self.assertEqual(parse_query("edges\t<\tY"), {'type': 'positional', 'entity': 'edges', 'operator': '<', 'axis': 'Y'}) # Tab as space

    def test_invalid_entity_for_directional_query(self):
        with self.assertRaisesRegex(ValueError, "Invalid entity type for directional query: 'edges'"):
            parse_query("edges # Z")
        with self.assertRaisesRegex(ValueError, "Invalid entity type for directional query: 'vertices'"):
            parse_query("vertices # -Y")

if __name__ == '__main__':
    unittest.main()
