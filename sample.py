import moldjson
import pathlib

# git clone https://github.com/KhronosGroup/glTF.git
path = pathlib.Path('gltf/specification/2.0/schema/glTF.schema.json')

schema = moldjson.parse_schema(path)

print(schema)
