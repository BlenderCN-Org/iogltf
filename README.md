# moldjson
jsonschema utility for python-3.7 typing.

plan

## generate

```py
import moldjson

schema = moldjson.parse_schema('path_to_json_schema')

with open('definitions.py', 'w') as f:
    f.write(schema.to_namedtuple())
```

## use

```py
import definitions

json_dict = get_json_dict()
root = definitions.from_json(json_dict)
```

## sample

```
$ git clone https://github.com/KhronosGroup/glTF.git
```
