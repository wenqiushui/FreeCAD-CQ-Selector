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
evaluator_module = importlib.import_module("FreeCAD-CQ-Selector.evaluator")
parser_module = importlib.import_module("FreeCAD-CQ-Selector.parser")

evaluate_query = evaluator_module.evaluate_query
Part = evaluator_module.Part
GEOMETRY_TOLERANCE = evaluator_module.GEOMETRY_TOLERANCE
MockShape = evaluator_module.MockShape
MockVector = evaluator_module.MockVector
MockBoundBox = evaluator_module.MockBoundBox
MockFace = evaluator_module.MockFace # This was MockFace from evaluator, which is correct
# If MockFace was intended to be Part.Face, it should be Part.Face from evaluator_module.Part
parse_query = parser_module.parse_query


class TestQueryEvaluator(unittest.TestCase):

    def setUp(self):
        """Set up mock shapes for testing."""
        # Define some common vectors
        self.vec_x_plus = MockVector(1, 0, 0)
        self.vec_x_minus = MockVector(-1, 0, 0)
        self.vec_y_plus = MockVector(0, 1, 0)
        self.vec_y_minus = MockVector(0, -1, 0)
        self.vec_z_plus = MockVector(0, 0, 1)
        self.vec_z_minus = MockVector(0, 0, -1)

        # Create mock sub-elements (faces, edges, vertices)
        # Faces
        self.face_top_z = Part.Face(normal_vector=self.vec_z_plus, center_of_mass=MockVector(0.5, 0.5, 1), bound_box=MockBoundBox(0,0,1,1,1,1)) # ZMax=1, ZMin=1
        self.face_bottom_z = Part.Face(normal_vector=self.vec_z_minus, center_of_mass=MockVector(0.5, 0.5, 0), bound_box=MockBoundBox(0,0,0,1,1,0)) # ZMin=0, ZMax=0

        # Adjust Z-bounds of other faces to not interfere with unique ZMax/ZMin tests
        self.face_front_x = Part.Face(normal_vector=self.vec_x_plus, center_of_mass=MockVector(1, 0.5, 0.5), bound_box=MockBoundBox(1,0,0.2,1,1,0.8)) # XMax=1
        self.face_back_x = Part.Face(normal_vector=self.vec_x_minus, center_of_mass=MockVector(0, 0.5, 0.5), bound_box=MockBoundBox(0,0,0.2,0,1,0.8)) # XMin=0
        self.face_right_y = Part.Face(normal_vector=self.vec_y_plus, center_of_mass=MockVector(0.5, 1, 0.5), bound_box=MockBoundBox(0,1,0.2,1,1,0.8)) # YMax=1
        self.face_left_y = Part.Face(normal_vector=self.vec_y_minus, center_of_mass=MockVector(0.5, 0, 0.5), bound_box=MockBoundBox(0,0,0.2,1,0,0.8)) # YMin=0

        # Edges
        # Edge along X axis at Y=0, Z=0, from X=0 to X=1
        self.edge_bottom_x_axis = Part.Edge(bound_box=MockBoundBox(0,0,0,1,0,0), center_of_mass=MockVector(0.5,0,0))
        # Edge along Y axis at X=1, Z=0, from Y=0 to Y=1
        self.edge_front_y_axis = Part.Edge(bound_box=MockBoundBox(1,0,0,1,1,0), center_of_mass=MockVector(1,0.5,0))
        # Edge along Z axis at X=1, Y=1, from Z=0 to Z=1
        self.edge_top_z_axis = Part.Edge(bound_box=MockBoundBox(1,1,0,1,1,1), center_of_mass=MockVector(1,1,0.5))

        # Vertices
        self.vertex_origin = Part.Vertex(bound_box=MockBoundBox(0,0,0,0,0,0), center_of_mass=MockVector(0,0,0))
        self.vertex_top_front_right = Part.Vertex(bound_box=MockBoundBox(1,1,1,1,1,1), center_of_mass=MockVector(1,1,1))
        self.vertex_custom_max_y = Part.Vertex(bound_box=MockBoundBox(0.5,1.5,0.5,0.5,1.5,0.5), center_of_mass=MockVector(0.5,1.5,0.5))


        # Main shape containing these sub-elements for general tests
        self.cube_shape = MockShape(sub_elements=[
            self.face_top_z, self.face_bottom_z, self.face_front_x, self.face_back_x, self.face_right_y, self.face_left_y,
            self.edge_bottom_x_axis, self.edge_front_y_axis, self.edge_top_z_axis,
            self.vertex_origin, self.vertex_top_front_right, self.vertex_custom_max_y
        ])
        # Ensure the mock shape itself has a BoundBox if needed for some tests (though not typical for root shape)
        self.cube_shape.BoundBox = MockBoundBox(0,0,0,1,1.5,1) # Covering all elements
        self.cube_shape.CenterOfMass = self.cube_shape.BoundBox.getCenter()


    def test_positional_query_faces_max_z(self):
        parsed = parse_query("faces > Z")
        selected = evaluate_query(self.cube_shape, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(self.face_top_z, selected)

    def test_positional_query_faces_min_z(self):
        parsed = parse_query("faces < Z")
        selected = evaluate_query(self.cube_shape, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(self.face_bottom_z, selected)

    def test_positional_query_edges_min_x(self):
        # edge_bottom_x_axis (XMin=0), edge_front_y_axis (XMin=1), edge_top_z_axis (XMin=1)
        # This test needs an edge that is uniquely min X.
        # Let's add a specific edge for this.
        edge_unique_min_x = Part.Edge(bound_box=MockBoundBox(-1,0,0,0,0,0), center_of_mass=MockVector(-0.5,0,0))
        shape_with_min_x_edge = MockShape(sub_elements=[edge_unique_min_x, self.edge_bottom_x_axis])

        parsed = parse_query("edges < X")
        selected = evaluate_query(shape_with_min_x_edge, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(edge_unique_min_x, selected)

    def test_positional_query_vertices_max_y_com(self):
        # vertex_origin (CoM.y=0), vertex_top_front_right (CoM.y=1), vertex_custom_max_y (CoM.y=1.5)
        parsed = parse_query("vertices | Y")
        selected = evaluate_query(self.cube_shape, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(self.vertex_custom_max_y, selected)

    def test_positional_query_empty_result(self):
        # Query for faces > X on a shape that only has faces with XMax = 0
        shape_at_origin_x = MockShape(sub_elements=[self.face_back_x, self.face_bottom_z]) # XMax for these is 0
        parsed = parse_query("faces > X") # This query asks for face with global max X
                                        # face_back_x has XMax = 0. face_bottom_z has XMax = 1.
                                        # So face_bottom_z should be selected.
                                        # To get empty, query for something non-existent.
        # Let's make a new shape where max X is not unique or condition is impossible
        custom_face1 = Part.Face(bound_box=MockBoundBox(0,0,0,0,1,1)) # XMax = 0
        custom_face2 = Part.Face(bound_box=MockBoundBox(0,0,0,0,1,1)) # XMax = 0
        shape_for_empty = MockShape(sub_elements=[custom_face1, custom_face2])
        # If we query "faces > X", both faces are at XMax=0. Both should be selected.
        # To get an empty result for ">" or "<", all elements must be identical in that extent.
        # Or, query a type that doesn't exist.
        parsed_no_edges = parse_query("edges > Z")
        shape_no_edges = MockShape(sub_elements=[self.face_top_z])
        selected = evaluate_query(shape_no_edges, parsed_no_edges)
        self.assertEqual(len(selected), 0)


    def test_directional_query_face_normal_z_plus(self):
        parsed = parse_query("faces # Z")
        selected = evaluate_query(self.cube_shape, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(self.face_top_z, selected)

    def test_directional_query_face_normal_x_minus(self):
        parsed = parse_query("faces # -X")
        selected = evaluate_query(self.cube_shape, parsed)
        self.assertEqual(len(selected), 1)
        self.assertIn(self.face_back_x, selected)

    def test_directional_query_non_face_entity(self):
        # Test that the parser raises an error for directional queries on non-face entities
        with self.assertRaisesRegex(ValueError, "Invalid entity type for directional query: 'edges'"):
             parse_query("edges # Z")

        with self.assertRaisesRegex(ValueError, "Invalid entity type for directional query: 'vertices'"):
             parse_query("vertices # X")

        # If a parsed query for a non-face (e.g. if manually constructed or if parser changes)
        # somehow gets to evaluator for directional type query:
        # The evaluator's _evaluate_directional_query also has a check and should return empty.
        parsed_for_eval_edges = {'type': 'directional', 'entity': 'edges', 'direction': 'Z'}
        selected_edges = evaluate_query(self.cube_shape, parsed_for_eval_edges)
        self.assertEqual(len(selected_edges), 0, "Directional query on 'edges' should return empty list from evaluator")

        parsed_for_eval_vertices = {'type': 'directional', 'entity': 'vertices', 'direction': 'Y'}
        selected_vertices = evaluate_query(self.cube_shape, parsed_for_eval_vertices)
        self.assertEqual(len(selected_vertices), 0, "Directional query on 'vertices' should return empty list from evaluator")


    def test_evaluator_type_error_invalid_shape(self):
        parsed = parse_query("faces > Z")
        with self.assertRaises(TypeError):
            evaluate_query("not_a_shape", parsed)
        with self.assertRaises(TypeError):
            evaluate_query(None, parsed)

    def test_evaluator_value_error_malformed_query_dict(self):
        # Malformed query that might bypass parser (e.g. if constructed manually)
        malformed_query_positional = {'type': 'positional', 'entity': 'faces'} # Missing operator/axis
        with self.assertRaises(ValueError):
            evaluate_query(self.cube_shape, malformed_query_positional)

        malformed_query_directional = {'type': 'directional', 'entity': 'faces'} # Missing direction
        with self.assertRaises(ValueError):
            evaluate_query(self.cube_shape, malformed_query_directional)

        unsupported_query_type = {'type': 'super_selector', 'entity': 'faces'}
        with self.assertRaises(ValueError):
            evaluate_query(self.cube_shape, unsupported_query_type)

    def test_tolerance_in_positional_queries(self):
        # Test '>' operator with tolerance
        face1 = Part.Face(bound_box=MockBoundBox(0,0,0,1.0,1,1))
        face2 = Part.Face(bound_box=MockBoundBox(0,0,0,1.0 - GEOMETRY_TOLERANCE / 2,1,1))
        face3 = Part.Face(bound_box=MockBoundBox(0,0,0,1.0 - GEOMETRY_TOLERANCE * 2,1,1))
        shape = MockShape(sub_elements=[face1, face2, face3])

        parsed = parse_query("faces > X")
        selected = evaluate_query(shape, parsed)
        self.assertEqual(len(selected), 2) # face1 and face2 should be selected
        self.assertIn(face1, selected)
        self.assertIn(face2, selected)
        self.assertNotIn(face3, selected)

    def test_tolerance_in_directional_queries(self):
        # Normal slightly off but within tolerance
        slightly_off_z_normal = MockVector(GEOMETRY_TOLERANCE / 10, 0, 1).normalize()
        face_slightly_off_z = Part.Face(normal_vector=slightly_off_z_normal)
        # Normal too far off - make x_component significantly larger
        too_far_off_z_normal = MockVector(0.1, 0, 1).normalize() # x=0.1 should make it deviate enough
        face_too_far_off_z = Part.Face(normal_vector=too_far_off_z_normal)

        shape = MockShape(sub_elements=[self.face_top_z, face_slightly_off_z, face_too_far_off_z])

        parsed = parse_query("faces # Z")
        selected = evaluate_query(shape, parsed)

        self.assertEqual(len(selected), 2)
        self.assertIn(self.face_top_z, selected)
        self.assertIn(face_slightly_off_z, selected)
        self.assertNotIn(face_too_far_off_z, selected)


if __name__ == '__main__':
    unittest.main()
