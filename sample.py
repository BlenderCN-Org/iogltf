import moldjson
import pathlib

# git clone https://github.com/KhronosGroup/glTF.git
path = pathlib.Path('gltf/specification/2.0/schema/glTF.schema.json')

schema = moldjson.parse_schema(path)

#print(schema)
schema.to_py(pathlib.Path('gltf.py'))

# git clone https://github.com/KhronosGroup/glTF-Sample-Models.git
import json
with pathlib.Path('glTF-Sample-Models/2.0/Avocado/glTF/Avocado.gltf').open() as f:
    js = json.load(f) 

import gltf
parsed = gltf.from_json(js)
print(parsed)
