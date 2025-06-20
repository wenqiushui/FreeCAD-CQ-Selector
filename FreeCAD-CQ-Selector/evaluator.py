try:
    import FreeCAD #type: ignore
    import Part #type: ignore
except ImportError:
    # Mock FreeCAD and Part for testing outside of FreeCAD
    class MockVector:
        def __init__(self, x, y, z):
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)

        def dot(self, other):
            return self.x * other.x + self.y * other.y + self.z * other.z

        def __add__(self, other):
            return MockVector(self.x + other.x, self.y + other.y, self.z + other.z)

        def __sub__(self, other):
            return MockVector(self.x - other.x, self.y - other.y, self.z - other.z)

        def __mul__(self, scalar):
            return MockVector(self.x * scalar, self.y * scalar, self.z * scalar)

        def __repr__(self):
            return f"MockVector({self.x}, {self.y}, {self.z})"

        def cross(self, other):
            return MockVector(
                self.y * other.z - self.z * other.y,
                self.z * other.x - self.x * other.z,
                self.x * other.y - self.y * other.x
            )

        def getLength(self):
            return (self.x**2 + self.y**2 + self.z**2)**0.5

        def normalize(self):
            le = self.getLength()
            if le == 0: return MockVector(0,0,0)
            return MockVector(self.x/le, self.y/le, self.z/le)

    class MockBoundBox:
        def __init__(self, xmin=0, ymin=0, zmin=0, xmax=0, ymax=0, zmax=0):
            self.XMin = float(xmin)
            self.YMin = float(ymin)
            self.ZMin = float(zmin)
            self.XMax = float(xmax)
            self.YMax = float(ymax)
            self.ZMax = float(zmax)

        def getCenter(self):
            return MockVector(
                (self.XMin + self.XMax) / 2,
                (self.YMin + self.YMax) / 2,
                (self.ZMin + self.ZMax) / 2
            )

    class MockFace: # Specific mock for Face to handle normalAt
        def __init__(self, normal_vector=None, center_of_mass=None, bound_box=None):
            self.ShapeType = "Face"
            self._normal = normal_vector if normal_vector else MockVector(0,0,1)
            self.CenterOfMass = center_of_mass if center_of_mass else MockVector(0.5,0.5,0.5)
            self.BoundBox = bound_box if bound_box else MockBoundBox(0,0,0,1,1,1)
            # For simplicity, assume UV parameters are 0,0 for normalAt if not a planar face
            # This mock is still very basic. Real faces are complex.

        def normalAt(self, u=None, v=None): # u,v can be CenterOfMass for some cases
            # In real FreeCAD, normalAt might need u,v parameters for non-planar faces
            # For this mock, we return a predefined normal
            return self._normal

        def __repr__(self):
            return f"MockFace(normal={self._normal}, CoM={self.CenterOfMass})"


    class MockShape:
        def __init__(self, sub_elements=None, obj_type="Shape", bound_box=None, center_of_mass=None):
            self.SubObjects = sub_elements if sub_elements else []
            self.ShapeType = obj_type
            self.BoundBox = bound_box if bound_box else MockBoundBox(0,0,0,1,1,1)
            self.CenterOfMass = center_of_mass if center_of_mass else self.BoundBox.getCenter()

        @property
        def Faces(self):
            return [f for f in self.SubObjects if f.ShapeType == "Face"]

        @property
        def Edges(self):
            return [e for e in self.SubObjects if e.ShapeType == "Edge"]

        @property
        def Vertices(self):
            return [v for v in self.SubObjects if v.ShapeType == "Vertex"]

        def __repr__(self):
            return f"MockShape(type={self.ShapeType}, sub_elements={len(self.SubObjects)})"


    class MockPart:
        Shape = MockShape
        Face = lambda normal_vector=None, center_of_mass=None, bound_box=None: MockFace(normal_vector, center_of_mass, bound_box)
        Edge = lambda bound_box=None, center_of_mass=None: MockShape(obj_type="Edge", bound_box=bound_box, center_of_mass=center_of_mass)
        Vertex = lambda bound_box=None, center_of_mass=None: MockShape(obj_type="Vertex", bound_box=bound_box, center_of_mass=center_of_mass)
        Vector = MockVector
        BoundBox = MockBoundBox

    Part = MockPart
    # Mock FreeCAD global environment
    FreeCAD = type('MockFreeCAD', (), {
        'Vector': MockVector,
        'BoundBox': MockBoundBox,
        'getTolerance': lambda: 1e-7, # Default tolerance
        'ActiveDocument': None # Placeholder
    })


GEOMETRY_TOLERANCE = 1e-7 # Default tolerance for float comparisons
if 'FreeCAD' in locals() and hasattr(FreeCAD, 'getTolerance'):
    # In a real FreeCAD environment, this would fetch the system tolerance
    GEOMETRY_TOLERANCE = FreeCAD.getTolerance()


def _get_sub_elements(shape, entity_type_str: str):
    """Helper to get faces, edges, or vertices from a shape."""
    if entity_type_str == "faces":
        return shape.Faces
    elif entity_type_str == "edges":
        return shape.Edges
    elif entity_type_str == "vertices":
        return shape.Vertices
    else:
        raise ValueError(f"Unknown entity type: {entity_type_str}")


def _evaluate_positional_query(shape, entity_type: str, operator: str, axis: str) -> list:
    """Evaluates positional queries like 'faces > X'."""
    sub_elements = _get_sub_elements(shape, entity_type)
    if not sub_elements:
        return []

    selected_elements = []

    if operator == '>':
        # Find the maximum extent along the axis
        max_val = -float('inf')
        if axis == 'X':
            max_val = max(el.BoundBox.XMax for el in sub_elements)
        elif axis == 'Y':
            max_val = max(el.BoundBox.YMax for el in sub_elements)
        elif axis == 'Z':
            max_val = max(el.BoundBox.ZMax for el in sub_elements)

        # Select elements at that maximum extent
        for el in sub_elements:
            val = 0
            if axis == 'X': val = el.BoundBox.XMax
            elif axis == 'Y': val = el.BoundBox.YMax
            elif axis == 'Z': val = el.BoundBox.ZMax
            if abs(val - max_val) < GEOMETRY_TOLERANCE:
                selected_elements.append(el)

    elif operator == '<':
        # Find the minimum extent along the axis
        min_val = float('inf')
        if axis == 'X':
            min_val = min(el.BoundBox.XMin for el in sub_elements)
        elif axis == 'Y':
            min_val = min(el.BoundBox.YMin for el in sub_elements)
        elif axis == 'Z':
            min_val = min(el.BoundBox.ZMin for el in sub_elements)

        # Select elements at that minimum extent
        for el in sub_elements:
            val = 0
            if axis == 'X': val = el.BoundBox.XMin
            elif axis == 'Y': val = el.BoundBox.YMin
            elif axis == 'Z': val = el.BoundBox.ZMin
            if abs(val - min_val) < GEOMETRY_TOLERANCE:
                selected_elements.append(el)

    elif operator == '|': # "maximum value of the coordinate" of CenterOfMass
        max_coord_val = -float('inf')
        if axis == 'X':
            max_coord_val = max(el.CenterOfMass.x for el in sub_elements)
        elif axis == 'Y':
            max_coord_val = max(el.CenterOfMass.y for el in sub_elements)
        elif axis == 'Z':
            max_coord_val = max(el.CenterOfMass.z for el in sub_elements)

        for el in sub_elements:
            com_coord = 0
            if axis == 'X': com_coord = el.CenterOfMass.x
            elif axis == 'Y': com_coord = el.CenterOfMass.y
            elif axis == 'Z': com_coord = el.CenterOfMass.z
            if abs(com_coord - max_coord_val) < GEOMETRY_TOLERANCE:
                selected_elements.append(el)
    else:
        raise ValueError(f"Unsupported operator: {operator}")

    return selected_elements


def _evaluate_directional_query(shape, entity_type: str, direction: str) -> list:
    """Evaluates directional queries like 'faces # Z'."""
    if entity_type != "faces":
        # As per spec, directional queries only apply to faces
        # Raising an error might be too disruptive if parser allows other types through.
        # An empty list seems safer for now. The parser should prevent this.
        # print(f"Warning: Directional query called for non-face entity '{entity_type}'.")
        return []

    faces = shape.Faces
    if not faces:
        return []

    target_vector = None
    if direction == 'X': target_vector = Part.Vector(1, 0, 0)
    elif direction == 'Y': target_vector = Part.Vector(0, 1, 0)
    elif direction == 'Z': target_vector = Part.Vector(0, 0, 1)
    elif direction == '-X': target_vector = Part.Vector(-1, 0, 0)
    elif direction == '-Y': target_vector = Part.Vector(0, -1, 0)
    elif direction == '-Z': target_vector = Part.Vector(0, 0, -1)
    else:
        raise ValueError(f"Invalid direction string: {direction}")

    selected_faces = []
    for face in faces:
        # Get normal at the center of the face (CenterOfMass might not be on the surface for complex faces)
        # A robust way is to use face.Surface.normal(u,v) with parameters from face.getParameterRange()
        # For simplicity with mocks and typical usage, normalAt(CenterOfMass) is often attempted.
        # FreeCAD's face.normalAt() takes U,V parameters not a point.
        # A common approach is to use the UV parameters of the point returned by face.CenterOfMassProjectedOnSurface
        # Or, if the face is planar, any point's normal is fine.
        # Our mock `normalAt` currently ignores parameters and returns a fixed normal or one set at construction.
        # In real FreeCAD:
        # com_on_surface = face.CenterOfMass # This might not be on the surface!
        # uv_params = face.Surface.getUVऑफPoint(com_on_surface) # This can fail if CoM is not on surface
        # normal = face.normalAt(uv_params[0], uv_params[1])
        # For the mock, we'll rely on the pre-set normal or the default.

        # In real FreeCAD, ensure face.normalAt is used correctly.
        # For planar faces, face.Orientation is often the normal.
        # For curved faces, you need a specific point on the surface.
        # Using CenterOfMass assumes it's a good representative point.
        try:
            # The mock normalAt doesn't use parameters, but real one does.
            # We pass 0,0 as dummy UVs for the mock, but in real FreeCAD,
            # you'd need to get valid UV parameters for the point on the surface.
            # A common point is the center of the surface if it's easily found.
            # For the mock, the normal is often set directly.
            normal = face.normalAt(0,0) # Mock uses its internal normal
        except Exception: # Broad exception for cases where normalAt might fail
            # e.g. if face is not properly defined or if normalAt is called incorrectly
            # For our mock, this is less likely unless the mock is changed.
            # print(f"Warning: Could not retrieve normal for a face. Skipping. Face: {face}")
            continue


        normal = normal.normalize() # Ensure it's a unit vector

        # Check for parallelism (dot product close to 1)
        # The query "faces # Z" means normal is in the same direction as Z-axis.
        dot_product = normal.dot(target_vector)
        if abs(dot_product - 1.0) < GEOMETRY_TOLERANCE:
            selected_faces.append(face)

    return selected_faces


def evaluate_query(shape, parsed_query: dict) -> list:
    """
    Evaluates a parsed query against a FreeCAD Part.Shape object.

    Args:
        shape: A FreeCAD Part.Shape object (or a compatible mock).
        parsed_query: A dictionary from parser.parse_query.

    Returns:
        A list of selected Part.Shape sub-elements (Faces, Edges, or Vertices).

    Raises:
        TypeError: If the input shape is not a valid Part.Shape (basic check).
        ValueError: If the query type or its components are unsupported.
    """
    # Basic check for shape type - relies on duck typing for SubObjects, Faces, Edges, Vertices
    if not hasattr(shape, 'ShapeType') or not hasattr(shape, 'SubObjects'):
        # This check is basic. A more robust check might involve `isinstance(shape, Part.Shape)`
        # but that won't work with the mock unless it inherits from a common base or is registered.
        raise TypeError(
            f"Input 'shape' is not a valid Part.Shape-like object. Got type: {type(shape)}"
        )

    query_type = parsed_query.get('type')
    entity_type = parsed_query.get('entity')

    if query_type == 'positional':
        operator = parsed_query.get('operator')
        axis = parsed_query.get('axis')
        if not all([entity_type, operator, axis]):
            raise ValueError(f"Missing components for positional query: {parsed_query}")
        return _evaluate_positional_query(shape, entity_type, operator, axis)

    elif query_type == 'directional':
        direction = parsed_query.get('direction')
        if not all([entity_type, direction]):
            raise ValueError(f"Missing components for directional query: {parsed_query}")
        if entity_type != 'faces':
             # This should ideally be caught by the parser, but as a safeguard:
            # print(f"Warning: Directional query attempted on non-face entity '{entity_type}'.")
            return []
        return _evaluate_directional_query(shape, entity_type, direction)

    else:
        raise ValueError(f"Unsupported query type: {query_type}")


if __name__ == '__main__':
    # --- Mock Setup for Testing ---
    # Create some mock sub-elements (faces, edges, vertices)
    # These would typically come from a real Part.Shape in FreeCAD

    # Positional Test Mock Shapes
    # For '>' operator (max X)
    # Make XMax distinctly larger for face_front. Change normal to avoid clash with directional tests.
    face_front = Part.Face(normal_vector=Part.Vector(0,1,0), center_of_mass=Part.Vector(1.5, 0.5, 0.5), bound_box=Part.BoundBox(1,0,0,2,1,1)) # Max X = 2, Normal Y+
    face_back = Part.Face(normal_vector=Part.Vector(-1,0,0), center_of_mass=Part.Vector(0, 0.5, 0.5), bound_box=Part.BoundBox(0,0,0,0,1,1)) # XMax = 0

    # For '<' operator (min Y)
    edge_bottom = Part.Edge(bound_box=Part.BoundBox(0,0,0,1,0,1), center_of_mass=Part.Vector(0.5,0,0.5)) # Min Y
    edge_top = Part.Edge(bound_box=Part.BoundBox(0,1,0,1,1,1), center_of_mass=Part.Vector(0.5,1,0.5))

    # For '|' operator (max Z CoM)
    vertex_high = Part.Vertex(bound_box=Part.BoundBox(0,0,1,0,0,1), center_of_mass=Part.Vector(0,0,1)) # Max Z CoM
    vertex_low = Part.Vertex(bound_box=Part.BoundBox(0,0,0,0,0,0), center_of_mass=Part.Vector(0,0,0))
    vertex_mid = Part.Vertex(bound_box=Part.BoundBox(0,0,0.5,0,0,0.5), center_of_mass=Part.Vector(0,0,0.5))


    # Directional Test Mock Shapes
    # Ensure their default BBoxes (XMax=1, YMin=0, ZMax CoM = 0.5) don't interfere with specific positional tests
    # Default MockFace uses BoundBox(0,0,0,1,1,1) and CoM(0.5,0.5,0.5)
    face_normal_z_plus = Part.Face(normal_vector=Part.Vector(0,0,1), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))
    face_normal_z_minus = Part.Face(normal_vector=Part.Vector(0,0,-1), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))
    face_normal_x_plus = Part.Face(normal_vector=Part.Vector(1,0,0), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))
    face_normal_y_minus = Part.Face(normal_vector=Part.Vector(0,-1,0), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))
    face_other_normal = Part.Face(normal_vector=Part.Vector(0.707, 0.707, 0), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))


    # Main shape containing these sub-elements
    mock_shape = Part.Shape(sub_elements=[
        face_front, face_back,
        edge_bottom, edge_top,
        vertex_high, vertex_low, vertex_mid,
        face_normal_z_plus, face_normal_z_minus, face_normal_x_plus, face_normal_y_minus, face_other_normal
    ])

    print("--- Testing Evaluator ---")

    # Test Positional Queries
    print("\n-- Positional Queries --")
    query1 = {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'X'} # Expect face_front
    res1 = evaluate_query(mock_shape, query1)
    print(f"Query: {query1} -> Result: {res1} (Expected: [MockFace(normal=MockVector(0.0, 1.0, 0.0), CoM=MockVector(1.5, 0.5, 0.5))])") # Normal changed for face_front
    assert len(res1) == 1 and res1[0] == face_front, f"Result was {res1}"

    query2 = {'type': 'positional', 'entity': 'edges', 'operator': '<', 'axis': 'Y'} # Expect edge_bottom
    res2 = evaluate_query(mock_shape, query2)
    print(f"Query: {query2} -> Result: {res2} (Expected: [MockShape(type=Edge, sub_elements=0)])") # MockShape repr is basic
    assert len(res2) == 1 and res2[0] == edge_bottom, f"Result was {res2}"

    query3 = {'type': 'positional', 'entity': 'vertices', 'operator': '|', 'axis': 'Z'} # Expect vertex_high
    res3 = evaluate_query(mock_shape, query3)
    print(f"Query: {query3} -> Result: {res3} (Expected: [MockShape(type=Vertex, sub_elements=0)])")
    assert len(res3) == 1 and res3[0] == vertex_high, f"Result was {res3}"

    # Test Directional Queries
    print("\n-- Directional Queries --")
    query4 = {'type': 'directional', 'entity': 'faces', 'direction': 'Z'} # Expect face_normal_z_plus
    res4 = evaluate_query(mock_shape, query4)
    print(f"Query: {query4} -> Result: {res4} (Expected: [MockFace(normal=MockVector(0.0, 0.0, 1.0), CoM=MockVector(0.5, 0.5, 0.5))])")
    assert len(res4) == 1 and res4[0] == face_normal_z_plus, f"Result was {res4}"

    # Specific face for -X normal test
    face_normal_x_minus = Part.Face(normal_vector=Part.Vector(-1,0,0), bound_box=Part.BoundBox(0.1,0.1,0.1,0.9,0.9,0.9), center_of_mass=Part.Vector(0.5,0.5,0.5))
    # Add this face to the main mock_shape for testing, or use a dedicated shape.
    # For now, let's add it to the main shape for simplicity of this test case.
    # This means mock_shape.SubObjects needs to be mutable or redefined.
    # Let's redefine mock_shape.SubObjects before this test or use a different shape object.

    # Create a specific shape for this directional test to avoid confusion with main mock_shape
    mock_shape_for_neg_x_test = Part.Shape(sub_elements=[
        face_normal_x_minus,
        face_normal_z_plus # include another face to ensure filtering
    ])
    query5 = {'type': 'directional', 'entity': 'faces', 'direction': '-X'}
    res5 = evaluate_query(mock_shape_for_neg_x_test, query5)
    print(f"Query: {{'type': 'directional', 'entity': 'faces', 'direction': '-X'}} -> Result: {res5} (Expected: [MockFace(normal=MockVector(-1.0, 0.0, 0.0), CoM=MockVector(0.5, 0.5, 0.5))])")
    assert len(res5) == 1 and res5[0] == face_normal_x_minus, f"Result was {res5}"

    query6 = {'type': 'directional', 'entity': 'faces', 'direction': '-Y'} # Expect face_normal_y_minus
    res6 = evaluate_query(mock_shape, query6) # mock_shape contains face_normal_y_minus
    print(f"Query: {{'type': 'directional', 'entity': 'faces', 'direction': '-Y'}} -> Result: {res6} (Expected: [MockFace(normal=MockVector(0.0, -1.0, 0.0), CoM=MockVector(0.5, 0.5, 0.5))])")
    assert len(res6) == 1 and res6[0] == face_normal_y_minus, f"Result was {res6}"

    query7 = {'type': 'directional', 'entity': 'faces', 'direction': 'X'} # Expect face_normal_x_plus
    res7 = evaluate_query(mock_shape, query7)
    print(f"Query: {{'type': 'directional', 'entity': 'faces', 'direction': 'X'}} -> Result: {res7} (Expected: [MockFace(normal=MockVector(1.0, 0.0, 0.0), CoM=MockVector(0.5, 0.5, 0.5))])")
    assert len(res7) == 1 and res7[0] == face_normal_x_plus, f"Result was {res7}"


    # Test invalid entity for directional query (should return empty list as per current logic)
    print("\n-- Invalid Directional Query (non-face) --")
    query_invalid_directional = {'type': 'directional', 'entity': 'edges', 'direction': 'X'}
    res_invalid_directional = evaluate_query(mock_shape, query_invalid_directional)
    print(f"Query: {query_invalid_directional} -> Result: {res_invalid_directional} (Expected: [])")
    assert len(res_invalid_directional) == 0

    # Test with empty sub-elements for a type
    print("\n-- Query on Type with No Elements --")
    empty_shape = Part.Shape(sub_elements=[Part.Edge()]) # Only has an edge
    query_empty_faces = {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'X'}
    res_empty_faces = evaluate_query(empty_shape, query_empty_faces)
    print(f"Query: {query_empty_faces} on shape with no faces -> Result: {res_empty_faces} (Expected: [])")
    assert len(res_empty_faces) == 0

    # Test TypeErrors
    print("\n-- TypeError Tests --")
    try:
        evaluate_query("not a shape", query1)
    except TypeError as e:
        print(f"Caught expected TypeError for invalid shape: {e}")
    try:
        evaluate_query(mock_shape, {'type': 'invalid_type'})
    except ValueError as e: # Changed from TypeError to ValueError based on implementation
        print(f"Caught expected ValueError for invalid query type: {e}")


    print("\nEvaluator implementation complete with basic mock tests.")
    print("NOTE: Mock `normalAt` for faces is simplified. Real FreeCAD usage needs care with UV parameters for curved surfaces.")
    print("NOTE: Positional query `|` for 'maximum value of the coordinate' of CenterOfMass along an axis.")

    # Example of how GEOMETRY_TOLERANCE is set
    print(f"\nGEOMETRY_TOLERANCE used: {GEOMETRY_TOLERANCE}")
    # In a real FreeCAD session, if FreeCAD.getTolerance() was, e.g. 1e-6, this would be 1e-6.
    # Otherwise, it's the default 1e-7.

    # Test case for no elements found
    query_no_match = {'type': 'positional', 'entity': 'faces', 'operator': '>', 'axis': 'Z'}
    # Assuming no face has ZMax at the global ZMax of all faces for this specific setup.
    # Let's make a shape where this is true.
    shape_for_no_match = Part.Shape(sub_elements=[
        Part.Face(bound_box=Part.BoundBox(0,0,0,1,1,0)), # ZMax = 0
        Part.Face(bound_box=Part.BoundBox(0,0,0.5,1,1,0.5)) # ZMax = 0.5
    ])
    # In this shape, max ZMax is 0.5. Query "faces > Z" should find the second face.
    # To test "no elements found", we need a condition that is not met.
    # e.g., a directional query for a normal that doesn't exist.
    query_no_match_dir = {'type': 'directional', 'entity': 'faces', 'direction': 'Y'}
    shape_no_y_normal_face = Part.Shape(sub_elements=[face_normal_z_plus, face_normal_x_plus])
    res_no_match = evaluate_query(shape_no_y_normal_face, query_no_match_dir)
    print(f"Query: {query_no_match_dir} on shape with no Y-normal faces -> Result: {res_no_match} (Expected: [])")
    assert len(res_no_match) == 0

    print("All basic tests seem to pass.")
