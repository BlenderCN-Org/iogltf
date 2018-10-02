#!/usr/bin/python
import json
import pathlib
from typing import Dict, Generator


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
        self.title = self.js.get('title', '').replace(' ', '')
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
            if key:
                return indent_space + key + ': ' + self.title + '{' +  '\n' + ''.join(v.dump(k, indent + 1) for k, v in self.properties.items()) + indent_space + '}\n'
            else:
                return indent_space + self.title + '{' +  '\n' + ''.join(v.dump(k, indent + 1) for k, v in self.properties.items()) + indent_space + '}\n'
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

        if not self.title and schema.title:
            self.title = schema.title

        for k, v in schema.properties.items():
            self.properties[k] = v

    def generate(self, used=set())->Generator[str, None, None]:
        if self.js_type == 'object':
            for _, v in self.properties.items():
                yield from v.generate(used)

        elif self.js_type == 'array':
            yield from self.items.generate(used)

        else:
            pass
            #yield self.js_type

        if self.title in used:
            pass
        elif self.js_type == 'object' and self.properties:
            used.add(self.title)
            yield f'class {self.title}:'
            yield '    def __init__(self)->None:'
            for k, v in self.properties.items():
                yield f'        self.{k} = None' 
            yield ''


def parse_schema(path: pathlib.Path)->JsonSchema:
    accessor = FileAccessor(path.parent)
    schema =  JsonSchema.parse(accessor, path.name)
    return schema


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("schema_json")
    parser.add_argument("-o","--out",
                        action = "store"
                        )
    args = parser.parse_args()

    path = pathlib.Path(args.schema_json)
    schema = parse_schema(path)

    if args.out:
        with pathlib.Path(args.out).open('w', encoding='utf-8') as f:
            f.writelines('\n'.join(schema.generate()))
    else:
        print(schema)
