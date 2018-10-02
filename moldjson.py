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
        self.title = self.js.get('title', '')
        self.properties: Dict[str, JsonSchema]  = {}
        if 'allOf' in self.js:
            # "allOf": [ { "$ref": "glTFProperty.schema.json" } ],
            for x in self.js['allOf']:
                if '$ref' in x:
                    sub_schema = JsonSchema.parse(accessor, x['$ref'])
                    self.merge(sub_schema)

        if 'properties' in self.js:
            for k, v in self.js['properties'].items():
                self.properties[k] = JsonSchema(v, accessor)

    def __str__(self)->str:
        return f'<{self.title}>'

    def merge(self, schema: 'JsonSchema')->None:
        for k, v in schema.properties.items():
            self.properties[k] = v


def parse_schema(path: pathlib.Path)->JsonSchema:
    accessor = FileAccessor(path.parent)
    schema =  JsonSchema.parse(accessor, path.name)
    return schema
