import os
import re
import ezdxf
from shapely.geometry import Polygon, Point
from Room_dimension.room_dimension import check_text_within_room, check_dimensions_match

def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

def save_copy_with_changes(original, new, rooms, texts):
    doc = ezdxf.readfile(original)

    for room in rooms:
        matched = False
        matched_count, total_count = 0, 0
        block_name = room['BlockName']

        if block_name in texts:
            for t in texts[block_name]:
                if check_text_within_room(room, t):
                    mc, tc = check_dimensions_match(room, [t])
                    matched_count += mc
                    total_count += tc
                    if mc > 0:
                        matched = True

        match_label = f"Match: {matched_count}/{total_count}"

        if block_name in doc.blocks:
            for ent in doc.blocks[block_name]:
                if ent.dxftype() == 'LWPOLYLINE' and ent.dxf.handle == room['Handle']:
                    center = (
                        (room['Polygon'].bounds[0] + room['Polygon'].bounds[2]) / 2,
                        (room['Polygon'].bounds[1] + room['Polygon'].bounds[3]) / 2
                    )
                    doc.modelspace().add_text(match_label, dxfattribs={'height': 5, 'insert': center})
                    ent.dxf.color = 3 if matched else 1

            for t in texts[block_name]:
                if check_text_within_room(room, t):
                    txt_entity = doc.entitydb.get(t['Handle'])
                    if txt_entity:
                        txt_entity.dxf.color = 3 if matched else 1

    doc.saveas(new)
