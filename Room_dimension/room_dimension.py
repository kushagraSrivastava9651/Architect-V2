import os
import re
import subprocess
import ezdxf
from shapely.geometry import Polygon, Point

 

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

def parse_dimension_text(text):
    match = re.search(r"(\d+)'(\d+)\"x(\d+)'(\d+)\"", text)
    if match:
        return tuple(map(int, match.groups()))
    return None

 
def clean_text_value(text):
    text = text.strip()
    text = re.sub(r"\d+'\d+\"x\d+'\d+\"$", "", text.strip())  # Remove 12'11"x11'10"
    text = re.sub(r"\d+\s*[xX]\s*\d+$", "", text.strip())     # Remove 3945 x 3606
    return text.strip()


def extract_room_boundaries(file_path, layer='A-Room Boundary'):
    doc = ezdxf.readfile(file_path)
    rooms = []
    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        for e in block:
            if e.dxftype() == 'LWPOLYLINE' and e.is_closed and e.dxf.layer.strip() == layer:
                points = [p[:2] for p in e.get_points()]
                poly = Polygon(points)
                if poly.is_valid:
                    minx, miny, maxx, maxy = poly.bounds
                    rooms.append({
                        'Handle': e.dxf.handle,
                        'Polygon': poly,
                        'Length': maxx - minx,
                        'Breadth': maxy - miny,
                        'LengthStr': mm_to_feet_inches_label(maxx - minx),
                        'BreadthStr': mm_to_feet_inches_label(maxy - miny),
                        'BlockName': block.name,
                        'Area': round(poly.area, 2)
                    })
    return rooms

def extract_block_text_info(file_path, layer='A-Text Main'):
    doc = ezdxf.readfile(file_path)
    texts = {}
    for insert in doc.modelspace().query('INSERT'):
        blk_name = insert.dxf.name
        blk = doc.blocks.get(blk_name)
        if not blk:
            continue
        entries = []
        for e in blk:
            if e.dxftype() in ('TEXT', 'MTEXT') and e.dxf.layer.strip() == layer:
                text_val = e.dxf.text if e.dxftype() == 'TEXT' else e.plain_text()
                entries.append({
                    'Handle': e.dxf.handle,
                    'Text': text_val,
                    'Position': tuple(round(c, 2) for c in e.dxf.insert)
                })
        if entries:
            texts[blk_name] = entries
    return texts

def check_text_within_room(room, text_info):
    return room['Polygon'].contains(Point(text_info['Position']))

def check_dimensions_match(room, text_info_list, tolerance=25.4):
    room_length_mm = room['Length']
    room_breadth_mm = room['Breadth']
    match_count = 0
    for text in text_info_list:
        parsed = parse_dimension_text(text['Text'])
        if parsed:
            l_ft, l_in, b_ft, b_in = parsed
            l_mm = feet_inches_to_mm(l_ft, l_in)
            b_mm = feet_inches_to_mm(b_ft, b_in)
            if abs(room_length_mm - l_mm) <= tolerance and abs(room_breadth_mm - b_mm) <= tolerance:
                match_count += 1
    return match_count, len(text_info_list)