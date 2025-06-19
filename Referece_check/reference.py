import os
import ezdxf
import re
import subprocess
from collections import defaultdict
from shapely.geometry import Polygon, Point
from ezdxf.math import Vec2, Vec3
from math import inf


def mm_to_feet_inches_label(mm):
    inches = mm / 25.4
    feet = int(inches // 12)
    inch_rem = round(inches % 12)
    if inch_rem == 12:
        feet += 1
        inch_rem = 0
    return f"{feet}'{inch_rem}\""

def feet_inches_to_mm(feet, inches):
    return (feet * 12 + inches) * 25.4

def line_length(entity):
    return (Vec3(entity.dxf.end) - Vec3(entity.dxf.start)).magnitude

def lwpolyline_length(entity):
    points = [Vec2(p[0], p[1]) for p in entity.get_points('xy')]
    return sum((points[i] - points[i - 1]).magnitude for i in range(1, len(points)))

def extract_room_dimensions(doc, layer='A-Room Boundary'):
    rooms = []
    for block in doc.blocks:
        for entity in block:
            if entity.dxftype() == 'LWPOLYLINE' and entity.dxf.layer == layer and entity.is_closed:
                poly = Polygon([point[:2] for point in entity.get_points()])
                if not poly.is_valid:
                    continue
                minx, miny, maxx, maxy = poly.bounds
                length = maxx - minx
                breadth = maxy - miny
                rooms.append((round(length), round(breadth)))
    return rooms

def extract_doors(doc, layer='A-Door Line'):
    lengths = []
    for block in doc.blocks:
        for entity in block:
            if entity.dxf.layer == layer and entity.dxftype() in ["LINE", "LWPOLYLINE"]:
                l = line_length(entity) if entity.dxftype() == "LINE" else lwpolyline_length(entity)
                lengths.append(round(l))
    return lengths

def get_entity_center(entity):
    if entity.dxftype() == "LINE":
        start = Vec2(entity.dxf.start)
        end = Vec2(entity.dxf.end)
        return (start + end) / 2
    elif entity.dxftype() == "LWPOLYLINE":
        points = [Vec2(p[0], p[1]) for p in entity.get_points('xy')]
        if not points:
            return Vec2(0, 0)
        centroid = sum(points, Vec2(0, 0)) / len(points)
        return centroid
    return Vec2(0, 0)

def visualize_mismatches(client_dxf_path, room_mismatches, door_mismatches, output_path):
    doc = ezdxf.readfile(client_dxf_path)
    msp = doc.modelspace()

    mismatched_doors = []

    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        for entity in block:
            if entity.dxftype() == "LWPOLYLINE" and entity.is_closed and entity.dxf.layer == "A-Room Boundary":
                poly = Polygon([pt[:2] for pt in entity.get_points()])
                if not poly.is_valid:
                    continue
                minx, miny, maxx, maxy = poly.bounds
                length = maxx - minx
                breadth = maxy - miny

                match_found = any(
                    abs(length - r[0]) <= 25.4 and abs(breadth - r[1]) <= 25.4
                    for r in room_mismatches
                )

                color = 1 if match_found else 3
                entity.dxf.color = color

                if not match_found:
                    x, y = poly.centroid.coords[0]
                    msp.add_text("Room Size Mismatch", dxfattribs={
                        "height": 10,
                        "insert": (x, y),
                        "color": 1
                    })

            if entity.dxf.layer == "A-Door Line" and entity.dxftype() in ("LINE", "LWPOLYLINE"):
                length = line_length(entity) if entity.dxftype() == "LINE" else lwpolyline_length(entity)
                match_found = any(abs(length - ref) <= 25.4 for ref in door_mismatches)
                color = 1 if match_found else 3
                entity.dxf.color = color

                if not match_found:
                    center = get_entity_center(entity)
                    msp.add_text("Door Length Mismatch", dxfattribs={
                        "height": 10,
                        "insert": (center.x, center.y),
                        "color": 1
                    })
                    mismatched_doors.append(center)

    # === Tag Coloring ===
    for entity in msp:
        if entity.dxftype() in ["TEXT", "MTEXT"] and entity.dxf.layer == "A-Door Tag":
            text_point = Vec2(entity.dxf.insert)
            closest_dist = inf
            for door_pt in mismatched_doors:
                if (Vec2(door_pt) - text_point).magnitude < 500:  # Within 500 mm (~20 inches)
                    entity.dxf.color = 1  # red
                    break

    doc.saveas(output_path)


def compare_values(ref_list, client_list, tolerance=25.4):
    mismatches = []
    for c in client_list:
        found = False
        for r in ref_list:
            if isinstance(c, tuple) and isinstance(r, tuple):
                if len(c) == len(r) == 2 and all(abs(c[i] - r[i]) <= tolerance for i in range(2)):
                    found = True
                    break
            else:
                if abs(c - r) <= tolerance:
                    found = True
                    break
        if not found:
            mismatches.append(c)
    return mismatches
