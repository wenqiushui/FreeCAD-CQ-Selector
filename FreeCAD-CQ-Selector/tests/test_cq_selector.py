import sys
import os
import unittest

# Add the project root directory (parent of 'FreeCAD-CQ-Selector') to sys.path
PACKAGE_PARENT = '../..' # Go up two levels: tests -> FreeCAD-CQ-Selector -> project_root
# Make __file__ absolute before getting its directory
ABS_FILE_PATH = os.path.abspath(os.path.expanduser(__file__))
SCRIPT_DIR = os.path.dirname(ABS_FILE_PATH)
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT))
sys.path.insert(0, PROJECT_ROOT) # Insert at beginning to ensure priority

import importlib
cq_selector_module = importlib.import_module("FreeCAD-CQ-Selector.cq_selector")
evaluator_module = importlib.import_module("FreeCAD-CQ-Selector.evaluator")

select = cq_selector_module.select
Part = evaluator_module.Part
MockShape = evaluator_module.MockShape
MockVector = evaluator_module.MockVector
MockBoundBox = evaluator_module.MockBoundBox
MockFace = evaluator_module.MockFace # This was MockFace from evaluator, which is correct


class TestCQSelectorAPI(unittest.TestCase):

    def setUp(self):
        """Set up a mock shape for API testing."""
        self.vec_z_plus = MockVector(0, 0, 1)
        self.vec_z_minus = MockVector(0, 0, -1)
        self.vec_x_plus = MockVector(1, 0, 0)

        self.face_top = Part.Face(normal_vector=self.vec_z_plus,
                                  center_of_mass=MockVector(0.5, 0.5, 1),
                                  bound_box=MockBoundBox(0,0,1,1,1,1)) # ZMax = 1
        self.face_bottom = Part.Face(normal_vector=self.vec_z_minus,
                                     center_of_mass=MockVector(0.5,0.5,0),
                                     bound_box=MockBoundBox(0,0,0,1,1,0)) # ZMin = 0, ZMax = 0
        self.face_front = Part.Face(normal_vector=self.vec_x_plus,
                                    center_of_mass=MockVector(1,0.5,0.5), # XMax = 1
                                    bound_box=MockBoundBox(1,0,0.1,1,1,0.8)) # ZMin = 0.1, ZMax = 0.8

        self.edge_x_axis = Part.Edge(bound_box=MockBoundBox(0,0,0,1,0,0),
                                     center_of_mass=MockVector(0.5,0,0)) # XMin = 0

        self.mock_shape_elements = [self.face_top, self.face_bottom, self.face_front, self.edge_x_axis]
        self.mock_shape = MockShape(sub_elements=self.mock_shape_elements)
        # Ensure the mock_shape itself quacks like a Part.Shape for the type check in `select`
        # The hasattr check in select() is the primary defense for mocks.
        # If Part.Shape is a concrete class (like evaluator's MockShape), this helps.
        if isinstance(Part.Shape, type): # Check if Part.Shape is a class
             self.mock_shape.__class__ = Part.Shape


    def test_valid_selection_face_max_z(self):
        selected_elements = select(self.mock_shape, "faces > Z")
        self.assertEqual(len(selected_elements), 1)
        self.assertIsInstance(selected_elements[0], MockFace) # Use MockFace class for isinstance
        self.assertEqual(selected_elements[0], self.face_top)

    def test_valid_selection_face_normal_x(self):
        selected_elements = select(self.mock_shape, "faces # X")
        self.assertEqual(len(selected_elements), 1)
        self.assertIsInstance(selected_elements[0], MockFace) # Use MockFace class for isinstance
        self.assertEqual(selected_elements[0], self.face_front)

    def test_valid_selection_edge_min_x(self):
        selected_elements = select(self.mock_shape, "edges < X")
        self.assertEqual(len(selected_elements), 1)
        # The mock Part.Edge returns a MockShape with ShapeType="Edge"
        self.assertTrue(hasattr(selected_elements[0], 'ShapeType') and selected_elements[0].ShapeType == "Edge")
        self.assertEqual(selected_elements[0], self.edge_x_axis)

    def test_selection_empty_result(self):
        selected_elements = select(self.mock_shape, "vertices > Z") # No vertices in mock_shape
        self.assertEqual(len(selected_elements), 0)

    def test_invalid_query_string(self):
        with self.assertRaises(ValueError):
            select(self.mock_shape, "this is not a valid query")

        with self.assertRaisesRegex(ValueError, "Invalid entity type for directional query"):
            select(self.mock_shape, "edges # Z")

    def test_invalid_input_shape_typeerror(self):
        with self.assertRaises(TypeError):
            select("not_a_part_shape_object", "faces > Z")

        with self.assertRaises(TypeError):
            select(None, "faces > Z")

    def test_integration_parser_evaluator(self):
        """
        Tests that `select` correctly wires parser and evaluator.
        A known query on a known shape should yield an expected result.
        """
        # Query: select faces whose normal is along the -Z axis
        # Expected: self.face_bottom
        selected_elements = select(self.mock_shape, "faces # -Z")
        self.assertEqual(len(selected_elements), 1)
        self.assertIsInstance(selected_elements[0], MockFace) # Use MockFace class for isinstance
        self.assertEqual(selected_elements[0], self.face_bottom)

        # Check a positional query too
        selected_elements_pos = select(self.mock_shape, "faces < Z")
        self.assertEqual(len(selected_elements_pos), 1)
        self.assertIsInstance(selected_elements_pos[0], MockFace) # Use MockFace class for isinstance
        self.assertEqual(selected_elements_pos[0], self.face_bottom)

if __name__ == '__main__':
    unittest.main()
