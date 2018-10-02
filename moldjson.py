import json
import pathlib
from typing import Dict


class FileAccessor:
    def __init__(self, dir: pathlib.Path)->None:
        self.dir = dir

    def read(self, rel: str)->str:
        path = self.dir / rel
        with path.open() as f:
            return f.read()


class JsonSchema:
    @staticmethod
    def parse(accessor: FileAccessor, name: str)->'JsonSchema':
        return JsonSchema(json.loads(accessor.read(name)), accessor)

    def __init__(self, js: dict, accessor: FileAccessor)->None:
        self.js = js
        self.js_type = self.js.get('type', 'object')
        self.title = self.js.get('title', '')
        self.properties: Dict[str, JsonSchema]  = {}

        if '$ref' in self.js:
            ref_schema = JsonSchema.parse(accessor, self.js['$ref'])
            self.merge(ref_schema)

        if 'allOf' in self.js:
            # "allOf": [ { "$ref": "glTFProperty.schema.json" } ],
            for x in self.js['allOf']:
                if '$ref' in x:
                    sub_schema = JsonSchema.parse(accessor, x['$ref'])
                    self.merge(sub_schema)

        if self.js_type == 'object':
            if 'properties' in self.js:
                for k, v in self.js['properties'].items():
                    if k in self.properties:
                        if v:
                            self.properties[k] = JsonSchema(v, accessor)
                        else:
                            # empty
                            pass
                    else:
                        self.properties[k] = JsonSchema(v, accessor)
        elif self.js_type == 'array':
            if 'items' in self.js:
                self.items = JsonSchema(self.js['items'], accessor)
                pass
        else:
            pass

    def dump(self, key: str, indent: int)->str:
        indent_space = "  " * indent
        if self.js_type == 'object':
            return indent_space + key + '{\n' + ''.join(v.dump(k, indent + 1) for k, v in self.properties.items()) + indent_space + '}\n'
        elif self.js_type == 'array':
            if self.items.js_type == 'object':
                return indent_space + key + '[\n' + self.items.dump('', indent + 1) + indent_space + ']\n'
            else:
                return indent_space + key + '[' + self.items.js_type + ']\n'
        else:
            if key:
                return indent_space + key + ': ' + self.js_type + '\n'
            else:
                return indent_space + self.js_type + '\n'

    def __str__(self)->str:
        return self.dump(self.title, 0)

    def merge(self, schema: 'JsonSchema')->None:
        if schema.js_type:
            self.js_type = schema.js_type

        for k, v in schema.properties.items():
            self.properties[k] = v


def parse_schema(path: pathlib.Path)->JsonSchema:
    accessor = FileAccessor(path.parent)
    schema =  JsonSchema.parse(accessor, path.name)
    return schema
