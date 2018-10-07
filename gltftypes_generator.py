import moldjson
import pathlib
from typing import Generator

# git clone https://github.com/KhronosGroup/glTF.git
path = pathlib.Path('gltf/specification/2.0/schema/glTF.schema.json')

schema = moldjson.parse_schema(path)

#print(schema)
schema.to_py(pathlib.Path('gltftypes.py'))

# git clone https://github.com/KhronosGroup/glTF-Sample-Models.git
def traverse(path: pathlib.Path)->Generator[pathlib.Path, None, None]:
    for x in path.iterdir():
        if x.is_dir():
            yield from traverse(x)
        else:
            if x.suffix == '.gltf':
                yield x

import json
import gltftypes
gltf_path = pathlib.Path('glTF-Sample-Models/2.0')
for x in traverse(gltf_path):
    print(x)
    with x.open() as f:
        js = json.load(f) 
        parsed = gltftypes.from_json(js)
        print(parsed)
