import moldjson


path = 'gltf/specification/2.0/schema/glTF.schema.json'

with open(path) as f:
    schema = moldjson.parse_schema(f.read())

print(schema)
