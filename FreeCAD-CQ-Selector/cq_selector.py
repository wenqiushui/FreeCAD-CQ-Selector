# Main API for FreeCAD-CQ-Selector

try:
    import FreeCAD #type: ignore
    import Part #type: ignore
except ImportError:
    # Use a simplified mock for Part.Shape for type hinting if FreeCAD is not available
    # The actual mocking for testing is expected to be more comprehensive in evaluator/parser
    print("Warning: FreeCAD module not found. Operating in mock mode for API definition.")

    # Attempt to use evaluator's mocks if available, as they are more complete
    # This helps the __main__ block function better in a standalone environment.
    evaluator_mock_source = None
    try:
        import evaluator as evaluator_mock_source_abs # Try absolute import first
        evaluator_mock_source = evaluator_mock_source_abs
        print("INFO: Using absolute import of evaluator for mocks in cq_selector.")
    except ImportError:
        try:
            from . import evaluator as evaluator_mock_source_rel # Then relative import
            evaluator_mock_source = evaluator_mock_source_rel
            print("INFO: Using relative import of evaluator for mocks in cq_selector.")
        except ImportError:
            print("Warning: evaluator.py not found or cannot be imported. Using basic mocks for Part/FreeCAD.")

    if evaluator_mock_source:
        MockShape = evaluator_mock_source.MockShape
        MockVector = evaluator_mock_source.MockVector
        MockBoundBox = evaluator_mock_source.MockBoundBox
        Part = evaluator_mock_source.Part
        FreeCAD = evaluator_mock_source.FreeCAD
    else: # Fallback to very basic mocks if evaluator_mock_source is still None
        MockShape = type('MockShape', (), {'ShapeType': 'Unknown'})
        MockVector = type('MockVector', (), {})
        MockBoundBox = type('MockBoundBox', (), {})
        _MockPart = type('MockPart', (), {'Shape': MockShape, 'Vector': MockVector, 'BoundBox': MockBoundBox})
        Part = _MockPart # type: ignore
        FreeCAD = type('MockFreeCAD', (), {'Vector': MockVector, 'BoundBox': MockBoundBox}) # type: ignore


# Placeholder for type hinting if Part cannot be imported or properly mocked early
if 'Part' not in globals() or not hasattr(Part, 'Shape'): # type: ignore
    class PartDef: #type: ignore
        class Shape:
            def __init__(self):
                self.ShapeType = "GenericShape" # Basic attribute
        Vector = MockVector # type: ignore
        BoundBox = MockBoundBox # type: ignore
    Part = PartDef # type: ignore

# Ensure Part.Shape is usable, even if it's a mock
if not hasattr(Part, 'Shape'): # type: ignore
    Part.Shape = type('Shape', (), {'ShapeType': 'FallbackShape'}) # type: ignore


# Conditional imports for parser and evaluator
try:
    # Try absolute import first (running script directly)
    from parser import parse_query
    from evaluator import evaluate_query
    print("INFO: Using absolute imports for parser and evaluator.")
except ImportError:
    # Fallback to relative import (running as part of a package)
    from .parser import parse_query
    from .evaluator import evaluate_query
    print("INFO: Using relative imports for parser and evaluator.")

def select(shape: Part.Shape, query: str) -> list[Part.Shape]: # type: ignore
    """
    Selects sub-elements (faces, edges, vertices) from a FreeCAD Part.Shape object
    based on a query string.

    The query language supports selecting entities by their position (e.g.,
    faces furthest in X direction) or orientation (e.g., faces whose normal
    is parallel to the Z-axis).

    Args:
        shape: A FreeCAD `Part.Shape` object from which to select sub-elements.
               This is typically obtained from a FreeCAD document object's
               `.Shape` attribute (e.g., `doc.getObject("MyCube").Shape`).
        query: A query string defining the selection criteria. Examples:
               - "faces > Z"  (faces with the maximum Z value of their bounding box)
               - "edges < Y"  (edges with the minimum Y value of their bounding box)
               - "vertices | X" (vertices with the maximum X coordinate of their center of mass)
               - "faces # -X" (faces whose normal vector is parallel to the negative X-axis)

    Returns:
        A list of `Part.Shape` objects representing the selected sub-elements
        (e.g., a list of `Part.Face` or `Part.Edge` objects).
        Returns an empty list if no elements match the query.

    Raises:
        TypeError: If the input `shape` is not a `Part.Shape` object.
        ValueError: If the `query` string is syntactically incorrect or uses
                    unsupported entities, operators, or axes/directions as per
                    the defined grammar.
        (Other exceptions from underlying geometry operations if they fail,
         though `evaluate_query` aims to handle common geometry issues).
    """
    # Validate input shape: must be an instance of Part.Shape
    # In FreeCAD, Part.Shape is a specific type.
    # The mock setup tries to make isinstance work, but it can be tricky.

    # Using hasattr for key properties as a more robust check with mocks
    expected_attrs = ["ShapeType", "BoundBox", "CenterOfMass", "Faces", "Edges", "Vertices"]
    is_shape_like = all(hasattr(shape, attr) for attr in expected_attrs) # type: ignore

    if not is_shape_like:
         # Try isinstance as a fallback, which might work if mocks are perfectly aligned or in real FreeCAD
        if not isinstance(shape, Part.Shape): # type: ignore
            raise TypeError(
                f"Input 'shape' must be a FreeCAD Part.Shape object or a compatible mock. "
                f"Received type: {type(shape)}. Lacking attributes: " # type: ignore
                f"{[attr for attr in expected_attrs if not hasattr(shape, attr)]}" # type: ignore
            )

    # Parse the query string
    # This may raise ValueError if the query is invalid
    parsed_query = parse_query(query) # type: ignore

    # Evaluate the parsed query against the shape
    # This may raise various errors if evaluation fails (e.g., TypeError from evaluator, geometric errors)
    selected_elements = evaluate_query(shape, parsed_query) # type: ignore

    return selected_elements # type: ignore


if __name__ == "__main__":
    # This example primarily tests the flow.
    # For full geometric evaluation, FreeCAD environment or more detailed mocks are needed.

    print("FreeCAD-CQ-Selector Example")

    # Attempt to use a mock shape if FreeCAD is not available.
    # Import evaluator to use its mocks if FreeCAD is not available
    # This specific import style is for when running this file directly.
    # If cq_selector is part of a package, `from . import evaluator` is used above.
    evaluator_module = None
    if 'FreeCAD' not in globals() or not hasattr(FreeCAD, 'ActiveDocument'): # A way to check if we're in mock mode
        try:
            from . import evaluator # if run as part of a package `python -m FreeCAD-CQ-Selector.cq_selector`
            evaluator_module = evaluator
            print("INFO: Using evaluator from package for mocks in __main__.")
        except ImportError:
            try:
                import evaluator # if FreeCAD-CQ-Selector is in PYTHONPATH and running script directly
                evaluator_module = evaluator
                print("INFO: Using evaluator from PYTHONPATH for mocks in __main__.")
            except ImportError:
                print("ERROR: __main__ example requires 'evaluator.py' to be accessible for mocks when FreeCAD is not running.")
                evaluator_module = None
    elif hasattr(FreeCAD, 'ActiveDocument'): # Real FreeCAD
        print("INFO: FreeCAD environment detected for __main__ example.")
        # We can try to use real Part objects if needed, but mocks are safer for a generic example.
        # The `evaluator_module` might still be useful for its MockShape definitions if we want to force mock usage.
        if not evaluator_module: # Try to load it for its mocks anyway, to standardize example
             try:
                from . import evaluator
                evaluator_module = evaluator
             except ImportError:
                try:
                    import evaluator
                    evaluator_module = evaluator
                except ImportError:
                    pass # Will proceed without evaluator mocks if in FreeCAD and they can't be found

    example_shape = None

    if evaluator_module:
        # Create a mock shape instance for testing using evaluator's mocks
        # Use Part.Face(), Part.Edge(), Part.Vertex() from the evaluator's mocked Part module
        mock_face1 = evaluator_module.Part.Face(
            normal_vector=evaluator_module.MockVector(0,0,1),
            center_of_mass=evaluator_module.MockVector(0.5,0.5,0.75),
            bound_box=evaluator_module.MockBoundBox(0,0,0.5,1,1,1) # ZMax = 1
        )
        # setattr(mock_face1, 'Name', "face_top_z") # Add name for nicer printing

        mock_face2 = evaluator_module.Part.Face(
            normal_vector=evaluator_module.MockVector(0,0,-1),
            center_of_mass=evaluator_module.MockVector(0.5,0.5,0.25),
            bound_box=evaluator_module.MockBoundBox(0,0,0,1,1,0.5) # ZMax = 0.5
        )
        # setattr(mock_face2, 'Name', "face_bottom_z")

        mock_edge1 = evaluator_module.Part.Edge(
            bound_box=evaluator_module.MockBoundBox(0.25,0,0,0.25,1,1), # YZ plane edge, X=0.25, YMin=0
            center_of_mass=evaluator_module.MockVector(0.25,0.5,0.5)
        )
        # setattr(mock_edge1, 'Name', "edge_min_x")

        mock_vertex1 = evaluator_module.Part.Vertex(
            center_of_mass=evaluator_module.MockVector(0.5, 0.8, 0.5) # Y=0.8
        )
        # setattr(mock_vertex1, 'Name', "vertex_high_y")

        example_shape_subs = [mock_face1, mock_face2, mock_edge1, mock_vertex1]
        example_shape = evaluator_module.MockShape(sub_elements=example_shape_subs)

        # Ensure the example_shape itself quacks like a Part.Shape for the type check in `select`
        # This is a bit of a hack. In real FreeCAD, objects come correctly typed.
        # The `is_shape_like` check in `select` using `hasattr` is the primary defense here for mocks.
        if not isinstance(example_shape, Part.Shape):
            example_shape.__class__ = Part.Shape

    elif 'FreeCAD' in globals() and hasattr(FreeCAD, 'ActiveDocument'):
        print("Attempting to create a real FreeCAD shape for example (Box).")
        try:
            # This requires a document. Let's ensure one exists or create it.
            doc = FreeCAD.ActiveDocument
            if not doc:
                doc = FreeCAD.newDocument("CQ_Selector_Test")

            if doc.getObject("TestBox"): # remove if exists
                doc.removeObject("TestBox")

            box = doc.addObject("Part::Box", "TestBox")
            doc.recompute()
            example_shape = box.Shape
            print(f"Successfully created a Part::Box. ShapeType: {example_shape.ShapeType}")
        except Exception as e:
            print(f"Error creating real FreeCAD shape for example: {e}")
            example_shape = None # Fallback if shape creation fails
    else:
        print("WARNING: Neither evaluator's mocks nor FreeCAD environment could be fully set up for __main__ example_shape.")


    queries = [
        ("faces > Z", True, "face_top_z"), # Expect mock_face1 (ZMax=1)
        ("edges < X", True, "edge_min_x"), # Expect mock_edge1 (XMin=0.25, if it's the only edge)
        ("vertices | Y", True, "vertex_high_y"), # Expect mock_vertex1 (CoM.y=0.8)
        ("faces # Z", True, "face_top_z"),    # Expect mock_face1 (normal 0,0,1)
        ("faces # -Z", True, "face_bottom_z"),# Expect mock_face2 (normal 0,0,-1)
        ("invalid query", False, None),
        ("faces & Z", False, None),
        ("edges > Z", True, None), # Query is valid, might return empty or some edge
    ]

    if example_shape:
        print(f"\n--- Running Queries on Shape: {type(example_shape)} ---")
        # Quick check of the shape's sub-elements if it's a mock
        if hasattr(example_shape, 'SubObjects'):
             print(f"  Shape has {len(example_shape.SubObjects)} sub-objects: "
                   f"{len(example_shape.Faces)} Faces, "
                   f"{len(example_shape.Edges)} Edges, "
                   f"{len(example_shape.Vertices)} Vertices.")


        for q_str, should_pass, expected_name_part in queries:
            print(f"\nTesting query: '{q_str}'")
            try:
                selected = select(example_shape, q_str)
                selected_names = []
                for s_idx, s_obj in enumerate(selected):
                    # Try to get a meaningful name or representation for mock objects
                    if hasattr(s_obj, 'Name'): name = s_obj.Name
                    elif hasattr(s_obj, 'TypeId'): name = s_obj.TypeId
                    elif hasattr(s_obj, 'ShapeType'): name = f"{s_obj.ShapeType}_{s_idx}"
                    else: name = str(s_obj)
                    selected_names.append(name)

                if should_pass:
                    print(f"  Selected {len(selected)} entities: {selected_names}")
                    if expected_name_part and selected:
                        # For mock tests, we often expect a single specific object
                        # This is a loose check based on our mock object naming convention
                        # Real objects in FreeCAD might not have such predictable 'Name' attributes from .select()
                        is_expected = False
                        if hasattr(selected[0], 'BoundBox') and expected_name_part == "face_top_z": # mock_face1
                             is_expected = abs(selected[0].BoundBox.ZMax - 1.0) < 1e-6
                        elif hasattr(selected[0], 'BoundBox') and expected_name_part == "edge_min_x": # mock_edge1
                             is_expected = abs(selected[0].BoundBox.XMin - 0.25) < 1e-6
                        elif hasattr(selected[0], 'CenterOfMass') and expected_name_part == "vertex_high_y": # mock_vertex1
                             is_expected = abs(selected[0].CenterOfMass.y - 0.8) < 1e-6
                        elif hasattr(selected[0], 'normalAt') and expected_name_part == "face_top_z": # mock_face1 normal
                             is_expected = selected[0].normalAt(0,0).z > 0.99
                        elif hasattr(selected[0], 'normalAt') and expected_name_part == "face_bottom_z": # mock_face2 normal
                             is_expected = selected[0].normalAt(0,0).z < -0.99

                        if not is_expected and expected_name_part:
                             print(f"  WARNING: Expected '{expected_name_part}' (or similar) but selection was different based on properties.")

                else: # Should not pass
                    print(f"  ERROR: Query '{q_str}' was expected to fail validation but passed. Selected: {selected_names}")
            except ValueError as e:
                if not should_pass:
                    print(f"  OK: Caught expected ValueError: {e}")
                else:
                    print(f"  ERROR: Query '{q_str}' caught unexpected ValueError: {e}")
            except TypeError as e:
                # TypeErrors can be expected if shape is wrong, but not for valid shape + invalid query
                if not should_pass and "Input 'shape' must be a FreeCAD Part.Shape object" in str(e): # Or similar message
                     print(f"  OK: Caught expected TypeError for invalid shape: {e}")
                else:
                     print(f"  ERROR: Query '{q_str}' caught unexpected TypeError: {e}")
            except Exception as e:
                print(f"  ERROR: Query '{q_str}' caught unexpected Exception: {e}")
    else:
        print("\nSkipping query execution in __main__ as no suitable example_shape was created.")

    print("\nNote: __main__ example results depend heavily on mock setup if FreeCAD is not present.")
    print("The mock names (e.g., 'face_top_z') are conceptual and not directly assigned as string names to mock objects in this basic example.")
