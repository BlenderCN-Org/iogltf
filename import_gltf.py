import json
import pathlib
from . import gltftypes
from typing import Set 


def load(filepath: str, global_matrix):
    print(global_matrix)
    path = pathlib.Path(filepath)
    with path.open() as f:
        gltf = gltftypes.from_json(json.load(f))
        print('load', gltf)

    return {'FINISHED'}
