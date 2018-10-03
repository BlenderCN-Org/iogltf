#!/usr/bin/python
import json
import pathlib
from typing import Dict, Generator, List, Any, Tuple, Optional


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
        self.description = self.js.get('description')
        # object
        self.properties: Dict[str, JsonSchema] = {}
        # int
        self.default = self.js.get('default', None)
        self.minimum = None
        # enum
        self.enum_labels: List[str] = []
        self.enum_values: List[Any] = []
        self.enum_type = None

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
        elif self.js_type == 'integer':
            if 'minimum' in self.js:
                self.minimum = self.js['minimum']
            pass
        else:
            pass

        if 'anyOf' in self.js:
            for x in self.js['anyOf']:
                if 'type' in x:
                    self.enum_type = x['type']

            values: List[Any] = []
            labels: List[str] = []
            for x in self.js['anyOf']:
                if 'enum' in x:
                    values = values + x['enum']
                    if self.enum_type == 'string':
                        labels.append(x['enum'][0].replace('/', '_'))
                    else:
                        labels.append(x['description'])
            self.enum_values = values
            self.enum_labels = labels

    def get_comment(self)->Optional[str]:
        if self.js_type == 'array':
            return self.items.description
        else:
            return self.description

    def dump(self, key: str, indent: int)->str:
        indent_space = "  " * indent
        if self.js_type == 'object':
            if key:
                return indent_space + key + ': ' + self.title + '{' + '\n' + ''.join(v.dump(k, indent + 1) for k, v in self.properties.items()) + indent_space + '}\n'
            else:
                return indent_space + self.title + '{' + '\n' + ''.join(v.dump(k, indent + 1) for k, v in self.properties.items()) + indent_space + '}\n'
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

        if not self.description and schema.description:
            self.description = schema.description

        for k, v in schema.properties.items():
            self.properties[k] = v

    def generate(self, key: str = None, used=set())->Generator[str, None, None]:
        if self.js_type == 'object':
            for k, v in self.properties.items():
                yield from v.generate(k, used)

        elif self.js_type == 'array':
            yield from self.items.generate(None, used)

        else:
            pass
            # yield self.js_type

        if self.title in used:
            pass
        else:
            if self.enum_type:
                enum_name = f'E_{key}'
                if enum_name not in used:
                    used.add(enum_name)
                    yield f'class {enum_name}(Enum):'
                    if self.enum_type == 'integer':
                        for x, y in zip(self.enum_labels, self.enum_values):
                            yield f'    {x} = {y}'
                    elif self.enum_type == 'string':
                        for x, y in zip(self.enum_labels, self.enum_values):
                            yield f'    {x} = "{y}"'
                    else:
                        raise Exception('unknown enum type')
                    yield ''

            elif self.js_type == 'object' and self.properties:
                used.add(self.title)
                yield f'class {self.title}:'
                yield f'    """{self.description}"""'
                yield '    def __init__(self, js: dict = None)->None:'
                for k, v in self.properties.items():
                    type_str, default_str, constructor = v.to_annotation(k)
                    yield f'        self.{k}: {type_str} = {default_str}'
                    comment = v.get_comment()
                    if comment:
                        yield f'        """{comment}"""'
                    yield f'        if (js and "{k}" in js):'
                    if constructor:
                        constructor = constructor % f'js["{k}"]'
                        yield f'            self.{k}: {type_str} = {constructor}'
                    else:
                        yield f'            self.{k}: {type_str} = js["{k}"]'
                    yield ''

    def to_annotation(self, key: str)->Tuple[str, str, Optional[str]]:
        if self.js_type == 'integer':
            return 'int', repr(self.default) if self.default != None else '-1', None

        elif self.js_type == 'number':
            return 'float', repr(self.default) if self.default != None else 'float("nan")', None

        elif self.js_type == 'string':
            return 'str', repr(self.default) if self.default != None else '""', None

        elif self.js_type == 'boolean':
            return 'bool', repr(self.default) if self.default != None else 'False', None

        elif self.js_type == 'object':
            if self.title == 'Extension' or self.title == 'Extras':
                return 'Dict[str, Any]', '{}', None
            elif self.title:
                return f'{self.title}', 'None', f'{self.title}(%s)'
            elif 'additionalProperties' in self.js:
                return 'Dict[str, int]', '{}', None

        elif self.js_type == 'array':
            if self.items.js_type == 'number':
                return 'List[float]', '[]', None
            elif self.items.js_type == 'integer':
                return 'List[int]', '[]', None
            elif self.items.js_type == 'string':
                return 'List[str]', '[]', None
            elif self.items.js_type == 'object':
                if self.items.title:
                    return f'List[{self.items.title}]', '[]', f'[{self.items.title}(x) for x in %s]'
                elif 'additionalProperties' in self.items.js:
                    return f'List[Dict[str, int]]', '[]', None
                else:
                    raise Exception('unknown type: ' + self.items.title)
            else:
                raise Exception('unknown type: ' + self.items.title)

        if self.enum_type:
            enum_name = f'E_{key}'
            if self.default:
                if self.enum_type == 'string':
                    return f'{enum_name}', f'{enum_name}("{self.default}")', f'{enum_name}(%s)'
                else:
                    return f'{enum_name}', f'{enum_name}({self.default})', f'{enum_name}(%s)'
            else:
                return f'Optional[{enum_name}]', 'None', f'{enum_name}(%s)'

        raise Exception('unknown type: ' + self.title)

    def to_py(self, path: pathlib.Path)->None:
        with path.open('w', encoding='utf-8') as f:
            f.write('''
from typing import Dict, Any, List, Optional
from enum import Enum

''')
            f.writelines('\n'.join(self.generate()))

            f.write(f'''
def from_json(js: dict)->{self.title}:
    return {self.title}(js)
''')


def parse_schema(path: pathlib.Path)->JsonSchema:
    accessor = FileAccessor(path.parent)
    schema = JsonSchema.parse(accessor, path.name)
    return schema


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("schema_json")
    parser.add_argument("-o", "--out",
                        action="store"
                        )
    args = parser.parse_args()

    path = pathlib.Path(args.schema_json)
    schema = parse_schema(path)

    if args.out:
        schema.to_py(pathlib.Path(args.out))
    else:
        print(schema)
