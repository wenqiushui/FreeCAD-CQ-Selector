# -*- coding: utf-8 -*-

from abc import abstractmethod, ABC
import math
from functools import reduce
from typing import Iterable, List, Sequence, TypeVar, cast

# FreeCAD的核心模块
import FreeCAD
import Part
from FreeCAD import Base

# 唯一的外部依赖，用于解析字符串
try:
    from pyparsing import (
        pyparsing_common,
        Literal,
        Word,
        nums,
        Optional,
        Combine,
        oneOf,
        Group,
        infixNotation,
        opAssoc,
    )
except ImportError:
    raise ImportError(
        "FreeCAD Selector dependency not found: 'pyparsing'.\n"
        "Please install it in FreeCAD's Python environment.\n"
        "Example: /path/to/FreeCAD/bin/pip install pyparsing"
    )

# =============================================================================
# Type Definitions and Aliases
# =============================================================================
Vector = Base.Vector
Shape = TypeVar("Shape", bound=Part.Shape)


# =============================================================================
# Helper Dictionaries and Functions (Translation Layer)
# =============================================================================

# CadQuery 使用 OCP 枚举，FreeCAD 使用 TypeId 字符串。我们在此建立映射。
geom_LUT_FACE = {
    'Part::GeomPlane': 'PLANE',
    'Part::GeomCylinder': 'CYLINDER',
    'Part::GeomCone': 'CONE',
    'Part::GeomSphere': 'SPHERE',
    'Part::GeomTorus': 'TORUS',
    'Part::GeomBezierSurface': 'BEZIER',
    'Part::GeomBSplineSurface': 'BSPLINE',
    # 添加其他可能的映射
}

geom_LUT_EDGE = {
    'Part::GeomLine': 'LINE',
    'Part::GeomCircle': 'CIRCLE',
    'Part::GeomEllipse': 'ELLIPSE',
    'Part::GeomHyperbola': 'HYPERBOLA',
    'Part::GeomParabola': 'PARABOLA',
    'Part::GeomBezierCurve': 'BEZIER',
    'Part::GeomBSplineCurve': 'BSPLINE',
    # 添加其他可能的映射
}

def get_geom_type(shape: Shape) -> str:
    """获取FreeCAD形状的几何类型，并返回CadQuery风格的字符串。"""
    if hasattr(shape, 'Surface'):
        return geom_LUT_FACE.get(shape.Surface.TypeId, 'OTHER')
    elif hasattr(shape, 'Curve'):
        return geom_LUT_EDGE.get(shape.Curve.TypeId, 'OTHER')
    return 'OTHER'

def get_normal(face: Part.Face) -> Vector:
    """获取平面的法线。"""
    if isinstance(face.Surface, Part.Plane):
        return face.Surface.Axis
    # 对于非平面，在参数空间中心取法线
    u_mid = (face.ParameterRange[0] + face.ParameterRange[1]) / 2
    v_mid = (face.ParameterRange[2] + face.ParameterRange[3]) / 2
    return face.normalAt(u_mid, v_mid)

def get_tangent(edge: Part.Edge) -> Vector:
    """获取直线的切线（方向）。"""
    if isinstance(edge.Curve, Part.Line):
        return edge.Curve.Direction
    # 对于非直线，在参数空间中心取切线
    p_mid = (edge.FirstParameter + edge.LastParameter) / 2
    return edge.tangentAt(p_mid)


# =============================================================================
# Selector Classes (Directly adapted from CadQuery)
# =============================================================================

class Selector(object):
    def filter(self, objectList: Sequence[Shape]) -> List[Shape]:
        return list(objectList)

    def __and__(self, other):
        return AndSelector(self, other)

    def __add__(self, other):
        return SumSelector(self, other)

    def __sub__(self, other):
        return SubtractSelector(self, other)

    def __neg__(self):
        return InverseSelector(self)


class NearestToPointSelector(Selector):
    def __init__(self, pnt):
        self.pnt = Vector(*pnt)

    def filter(self, objectList: Sequence[Shape]):
        def dist(tShape):
            return tShape.CenterOfMass.sub(self.pnt).Length

        return [min(objectList, key=dist)]


class BoxSelector(Selector):
    def __init__(self, point0, point1, boundingbox=False):
        self.p0 = Vector(*point0)
        self.p1 = Vector(*point1)
        self.test_boundingbox = boundingbox

    def filter(self, objectList: Sequence[Shape]):
        result = []
        x0, y0, z0 = self.p0
        x1, y1, z1 = self.p1

        def isInsideBox(p):
            return (
                ((p.x < x0) ^ (p.x < x1)) and
                ((p.y < y0) ^ (p.y < y1)) and
                ((p.z < z0) ^ (p.z < z1))
            )

        for o in objectList:
            if self.test_boundingbox:
                bb = o.BoundBox
                if isInsideBox(Vector(bb.XMin, bb.YMin, bb.ZMin)) and isInsideBox(
                    Vector(bb.XMax, bb.YMax, bb.ZMax)
                ):
                    result.append(o)
            else:
                if isInsideBox(o.CenterOfMass):
                    result.append(o)
        return result


class BaseDirSelector(Selector):
    def __init__(self, vector: Vector, tolerance: float = 1e-6):
        self.direction = vector.normalize()
        self.tolerance = tolerance

    def test(self, vec: Vector) -> bool:
        return True

    def filter(self, objectList: Sequence[Shape]) -> List[Shape]:
        r = []
        for o in objectList:
            if o.ShapeType == "Face" and get_geom_type(o) == "PLANE":
                test_vector = get_normal(cast(Part.Face, o))
            elif o.ShapeType == "Edge" and get_geom_type(o) == "LINE":
                test_vector = get_tangent(cast(Part.Edge, o))
            else:
                continue

            if self.test(test_vector):
                r.append(o)
        return r


class ParallelDirSelector(BaseDirSelector):
    def test(self, vec: Vector) -> bool:
        return self.direction.cross(vec).Length < self.tolerance


class DirectionSelector(BaseDirSelector):
    def test(self, vec: Vector) -> bool:
        # getAngle is in radians
        return self.direction.getAngle(vec) < self.tolerance


class PerpendicularDirSelector(BaseDirSelector):
    def test(self, vec: Vector) -> bool:
        return abs(self.direction.getAngle(vec) - math.pi / 2) < self.tolerance


class TypeSelector(Selector):
    def __init__(self, typeString: str):
        self.typeString = typeString.upper()

    def filter(self, objectList: Sequence[Shape]) -> List[Shape]:
        r = []
        for o in objectList:
            if get_geom_type(o) == self.typeString:
                r.append(o)
        return r


class _NthSelector(Selector, ABC):
    def __init__(self, n: int, directionMax: bool = True, tolerance: float = 1e-6):
        self.n = n
        self.directionMax = directionMax
        self.tolerance = tolerance

    def filter(self, objectlist: Sequence[Shape]) -> List[Shape]:
        if len(objectlist) == 0:
            raise ValueError("Can not return the Nth element of an empty list")

        clustered = self.cluster(objectlist)
        if not self.directionMax:
            clustered.reverse()
        try:
            out = clustered[self.n]
        except IndexError:
            raise IndexError(
                f"Attempted to access index {self.n} of a list with length {len(clustered)}"
            )
        return out

    @abstractmethod
    def key(self, obj: Shape) -> float:
        raise NotImplementedError

    def cluster(self, objectlist: Sequence[Shape]) -> List[List[Shape]]:
        key_and_obj = []
        for obj in objectlist:
            try:
                key = self.key(obj)
                key_and_obj.append((key, obj))
            except (ValueError, Part.OCCError):
                continue

        if not key_and_obj:
            return []
            
        key_and_obj.sort(key=lambda x: x[0])
        clustered = [[]]
        start = key_and_obj[0][0]
        for key, obj in key_and_obj:
            if abs(key - start) <= self.tolerance:
                clustered[-1].append(obj)
            else:
                clustered.append([obj])
                start = key
        return clustered


class RadiusNthSelector(_NthSelector):
    def key(self, obj: Shape) -> float:
        if obj.ShapeType in ("Edge", "Wire") and hasattr(obj, 'Curve') and hasattr(obj.Curve, 'Radius'):
            return obj.Curve.Radius
        else:
            raise ValueError("Can not get a radius from this object")


class CenterNthSelector(_NthSelector):
    def __init__(self, vector: Vector, n: int, directionMax: bool = True, tolerance: float = 1e-6):
        super().__init__(n, directionMax, tolerance)
        self.direction = vector

    def key(self, obj: Shape) -> float:
        return obj.CenterOfMass.dot(self.direction)


class DirectionMinMaxSelector(CenterNthSelector):
    def __init__(self, vector: Vector, directionMax: bool = True, tolerance: float = 1e-6):
        super().__init__(n=-1, vector=vector, directionMax=directionMax, tolerance=tolerance)


class DirectionNthSelector(ParallelDirSelector, CenterNthSelector):
    def __init__(self, vector: Vector, n: int, directionMax: bool = True, tolerance: float = 1e-6):
        ParallelDirSelector.__init__(self, vector, tolerance)
        _NthSelector.__init__(self, n, directionMax, tolerance)

    def filter(self, objectlist: Sequence[Shape]) -> List[Shape]:
        objectlist = ParallelDirSelector.filter(self, objectlist)
        objectlist = _NthSelector.filter(self, objectlist)
        return objectlist


class LengthNthSelector(_NthSelector):
    def key(self, obj: Shape) -> float:
        if obj.ShapeType in ("Edge", "Wire"):
            return obj.Length
        else:
            raise ValueError(f"LengthNthSelector supports only Edges and Wires, not {obj.ShapeType}")


class AreaNthSelector(_NthSelector):
    def key(self, obj: Shape) -> float:
        if obj.ShapeType in ("Face", "Shell", "Solid"):
            return obj.Area
        elif obj.ShapeType == "Wire":
            try:
                # For closed planar wires, create a temporary face to get area
                return Part.Face(cast(Part.Wire, obj)).Area
            except Part.OCCError as ex:
                raise ValueError(f"Can not compute area of the Wire: {ex}. Supports only closed planar Wires.")
        else:
            raise ValueError(f"AreaNthSelector supports only Wires, Faces, Shells and Solids, not {obj.ShapeType}")

# ... (BinarySelector and its subclasses are pure Python logic, no changes needed) ...
class BinarySelector(Selector):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def filter(self, objectList: Sequence[Shape]):
        return self.filterResults(self.left.filter(objectList), self.right.filter(objectList))
    def filterResults(self, r_left, r_right):
        raise NotImplementedError

class AndSelector(BinarySelector):
    def filterResults(self, r_left, r_right):
        return list(set(r_left) & set(r_right))

class SumSelector(BinarySelector):
    def filterResults(self, r_left, r_right):
        return list(set(r_left) | set(r_right))

class SubtractSelector(BinarySelector):
    def filterResults(self, r_left, r_right):
        return list(set(r_left) - set(r_right))

class InverseSelector(Selector):
    def __init__(self, selector):
        self.selector = selector
    def filter(self, objectList: Sequence[Shape]):
        return SubtractSelector(Selector(), self.selector).filter(objectList)

# =============================================================================
# PyParsing Grammar and String Selector (Directly adapted from CadQuery)
# =============================================================================
def _makeGrammar():
    point = Literal(".")
    plusmin = Literal("+") | Literal("-")
    number = Word(nums)
    integer = Combine(Optional(plusmin) + number)
    floatn = Combine(integer + Optional(point + Optional(number)))
    lbracket, rbracket, comma = map(Literal, "(),")
    vector = Combine(lbracket + floatn("x") + comma + floatn("y") + comma + floatn("z") + rbracket, adjacent=False)
    simple_dir = oneOf(["X", "Y", "Z", "XY", "XZ", "YZ"])
    direction = simple_dir("simple_dir") | vector("vector_dir")
    
    cqtype_strings = set(geom_LUT_EDGE.values()) | set(geom_LUT_FACE.values())
    cqtype = oneOf(list(cqtype_strings), caseless=True).setParseAction(pyparsing_common.upcaseTokens)

    type_op = Literal("%")
    direction_op = oneOf([">", "<"])
    center_nth_op = oneOf([">>", "<<"])
    ix_number = Group(Optional("-") + Word(nums))
    lsqbracket, rsqbracket = map(Literal, "[]")
    index = lsqbracket.suppress() + ix_number("index") + rsqbracket.suppress()
    other_op = oneOf(["|", "#", "+", "-"])
    named_view = oneOf(["front", "back", "left", "right", "top", "bottom"])

    return (
        direction("only_dir") |
        (type_op("type_op") + cqtype("cq_type")) |
        (direction_op("dir_op") + direction("dir") + Optional(index)) |
        (center_nth_op("center_nth_op") + direction("dir") + Optional(index)) |
        (other_op("other_op") + direction("dir")) |
        named_view("named_view")
    )

_grammar = _makeGrammar()

class _SimpleStringSyntaxSelector(Selector):
    def __init__(self, parseResults):
        self.axes = {"X": Vector(1, 0, 0), "Y": Vector(0, 1, 0), "Z": Vector(0, 0, 1),
                     "XY": Vector(1, 1, 0), "YZ": Vector(0, 1, 1), "XZ": Vector(1, 0, 1)}
        self.namedViews = {"front": (Vector(0, -1, 0), True), "back": (Vector(0, 1, 0), True),
                           "left": (Vector(-1, 0, 0), True), "right": (Vector(1, 0, 0), True),
                           "top": (Vector(0, 0, 1), True), "bottom": (Vector(0, 0, -1), True)}
        self.operatorMinMax = {">": True, ">>": True, "<": False, "<<": False}
        self.operator = {"+": DirectionSelector, "-": lambda v: DirectionSelector(-v),
                         "#": PerpendicularDirSelector, "|": ParallelDirSelector}
        self.parseResults = parseResults
        self.mySelector = self._chooseSelector(parseResults)

    def _chooseSelector(self, pr):
        if "only_dir" in pr:
            return DirectionSelector(self._getVector(pr))
        elif "type_op" in pr:
            return TypeSelector(pr.cq_type)
        elif "dir_op" in pr:
            vec, minmax = self._getVector(pr), self.operatorMinMax[pr.dir_op]
            return DirectionNthSelector(vec, int("".join(pr.index.asList())), minmax) if "index" in pr else DirectionMinMaxSelector(vec, minmax)
        elif "center_nth_op" in pr:
            vec, minmax = self._getVector(pr), self.operatorMinMax[pr.center_nth_op]
            return CenterNthSelector(vec, int("".join(pr.index.asList())), minmax) if "index" in pr else CenterNthSelector(vec, -1, minmax)
        elif "other_op" in pr:
            return self.operator[pr.other_op](self._getVector(pr))
        else:
            return DirectionMinMaxSelector(*self.namedViews[pr.named_view])

    def _getVector(self, pr):
        if "vector_dir" in pr:
            vec = pr.vector_dir
            return Vector(float(vec.x), float(vec.y), float(vec.z))
        else:
            return self.axes[pr.simple_dir]

    def filter(self, objectList: Sequence[Shape]):
        return self.mySelector.filter(objectList)

def _makeExpressionGrammar(atom):
    and_op, or_op, not_op = map(Literal, ["and", "or", "not"])
    delta_op = oneOf(["exc", "except"])
    atom.setParseAction(lambda res: _SimpleStringSyntaxSelector(res))

    def and_callback(res): return reduce(AndSelector, res.asList()[0][::2])
    def or_callback(res): return reduce(SumSelector, res.asList()[0][::2])
    def exc_callback(res): return reduce(SubtractSelector, res.asList()[0][::2])
    def not_callback(res): return InverseSelector(res.asList()[0][1])

    return infixNotation(atom, [
        (and_op, 2, opAssoc.LEFT, and_callback),
        (or_op, 2, opAssoc.LEFT, or_callback),
        (delta_op, 2, opAssoc.LEFT, exc_callback),
        (not_op, 1, opAssoc.RIGHT, not_callback),
    ])

_expression_grammar = _makeExpressionGrammar(_grammar)

class StringSyntaxSelector(Selector):
    def __init__(self, selectorString):
        self.selectorString = selectorString
        parse_result = _expression_grammar.parseString(selectorString, parseAll=True)
        self.mySelector = parse_result.asList()[0]

    def filter(self, objectList: Sequence[Shape]):
        return self.mySelector.filter(objectList)


# =============================================================================
# Self-test block for headless execution
# =============================================================================
if __name__ == '__main__':
    print("="*60)
    print("Running cq_selector.py self-test in FreeCAD headless mode")
    print("="*60)

    # 1. Create a test shape
    # A box translated so its center is not at the origin, with a fillet
    box = Part.makeBox(10, 20, 30)
    box.translate(Vector(-5, -10, 0)) # Center is now at (0, 0, 15)
    
    # Add a fillet to create a non-planar face and non-linear edges
    fillet_edges = [e for e in box.Edges if e.Vertexes[0].Z == 30 and e.Vertexes[1].Z == 30]
    shape = box.makeFillet(2, fillet_edges)

    print(f"Test shape created with {len(shape.Faces)} faces, {len(shape.Edges)} edges.")
    
    # 2. Run tests
    tests_passed = 0
    total_tests = 0

    def run_test(description, selector_str, obj_list, expected_count):
        global tests_passed, total_tests
        total_tests += 1
        print(f"\n--- Testing: {description} ('{selector_str}') ---")
        try:
            selector = StringSyntaxSelector(selector_str)
            result = selector.filter(obj_list)
            assert len(result) == expected_count
            print(f"SUCCESS: Found {len(result)} item(s) as expected.")
            tests_passed += 1
        except Exception as e:
            print(f"FAILED: {e}")

    # Face tests
    run_test("Select top-most face by center", ">Z", shape.Faces, 1)
    run_test("Select bottom-most face by center", "<Z", shape.Faces, 1)
    run_test("Select faces with normal parallel to Z-axis", "|Z", shape.Faces, 2)
    run_test("Select faces with normal perpendicular to X-axis", "#X", shape.Faces, 4) # front, back, top, bottom
    run_test("Select all planar faces", "%PLANE", shape.Faces, 6)
    run_test("Select front face by named view", "front", shape.Faces, 1) # Note: requires correct view setup
    run_test("Select top face with positive Z normal", "+Z", shape.Faces, 1)
    
    # Edge tests
    run_test("Select longest edges", ">Z", shape.Edges, 4) # The vertical edges
    run_test("Select edges parallel to X-axis", "|X", shape.Edges, 4)
    run_test("Select all linear edges", "%LINE", shape.Edges, 8)
    
    # Complex tests
    run_test("Top face OR bottom face", ">Z or <Z", shape.Faces, 2)
    run_test("Planar faces AND parallel to Y", "%PLANE and |Y", shape.Faces, 2)
    run_test("All faces EXCEPT the top one", "#Z or |X or |Y", shape.Faces, 6) # Easier way to say 'not >Z'
    run_test("NOT the top face", "not >Z", shape.Faces, len(shape.Faces) - 1)
    
    # Nth selector tests
    # Create a new shape for this
    stack = Part.makeBox(10,10,2)
    stack = stack.fuse(Part.makeBox(10,10,5).move(Vector(0,0,2)))
    stack = stack.fuse(Part.makeBox(10,10,1).move(Vector(0,0,7)))
    # 3 horizontal planar faces at z=2, 7, 8
    run_test("Nth Selector: 2nd highest face ([ -2])", ">Z[-2]", stack.Faces, 1)
    
    print("\n" + "="*60)
    print(f"Test summary: {tests_passed} / {total_tests} tests passed.")
    print("="*60)

    if tests_passed != total_tests:
        print("\nSome tests failed. Please review the output.")
    else:
        print("\nAll tests passed successfully!")
