# moldjson
jsonschema utility for python-3.7 typing.

## parse

```py
import moldjson
import pathlib

# git clone https://github.com/KhronosGroup/glTF.git
path = pathlib.Path('gltf/specification/2.0/schema/glTF.schema.json')

schema = moldjson.parse_schema(path)

print(schema)

'''
glTF{
  extensions{
  }
  extras{
  }
  extensionsUsed[string]
  extensionsRequired[string]
  accessors[
    {
      extensions{
      }
      extras{
      }
      name: string
      bufferView: integer
      byteOffset: integer
      componentType{
      }
      normalized: boolean
      count: integer
      type{
      }
      max[number]
      min[number]
      sparse{
        extensions{
        }
        extras{
        }
        count: integer
        indices{
          extensions{
          }
          extras{
          }
          bufferView: integer
          byteOffset: integer
          componentType{
          }
        }
        values{
          extensions{
          }
          extras{
          }
          bufferView: integer
          byteOffset: integer
        }
      }
    }
  ]
  animations[
    {
      extensions{
      }
      extras{
      }
      name: string
      channels[
        {
          extensions{
          }
          extras{
          }
          sampler: integer
          target{
            extensions{
            }
            extras{
            }
            node: integer
            path{
            }
          }
        }
      ]
      samplers[
        {
          extensions{
          }
          extras{
          }
          input: integer
          interpolation{
          }
          output: integer
        }
      ]
    }
  ]
  asset{
    extensions{
    }
    extras{
    }
    copyright: string
    generator: string
    version: string
    minVersion: string
  }
  buffers[
    {
      extensions{
      }
      extras{
      }
      name: string
      uri: string
      byteLength: integer
    }
  ]
  bufferViews[
    {
      extensions{
      }
      extras{
      }
      name: string
      buffer: integer
      byteOffset: integer
      byteLength: integer
      byteStride: integer
      target{
      }
    }
  ]
  cameras[
    {
      extensions{
      }
      extras{
      }
      name: string
      orthographic{
        extensions{
        }
        extras{
        }
        xmag: number
        ymag: number
        zfar: number
        znear: number
      }
      perspective{
        extensions{
        }
        extras{
        }
        aspectRatio: number
        yfov: number
        zfar: number
        znear: number
      }
      type{
      }
    }
  ]
  images[
    {
      extensions{
      }
      extras{
      }
      name: string
      uri: string
      mimeType{
      }
      bufferView: integer
    }
  ]
  materials[
    {
      extensions{
      }
      extras{
      }
      name: string
      pbrMetallicRoughness{
        extensions{
        }
        extras{
        }
        baseColorFactor[number]
        baseColorTexture{
          extensions{
          }
          extras{
          }
          index: integer
          texCoord: integer
        }
        metallicFactor: number
        roughnessFactor: number
        metallicRoughnessTexture{
          extensions{
          }
          extras{
          }
          index: integer
          texCoord: integer
        }
      }
      normalTexture{
        extensions{
        }
        extras{
        }
        index: integer
        texCoord: integer
        scale: number
      }
      occlusionTexture{
        extensions{
        }
        extras{
        }
        index: integer
        texCoord: integer
        strength: number
      }
      emissiveTexture{
        extensions{
        }
        extras{
        }
        index: integer
        texCoord: integer
      }
      emissiveFactor[number]
      alphaMode{
      }
      alphaCutoff: number
      doubleSided: boolean
    }
  ]
  meshes[
    {
      extensions{
      }
      extras{
      }
      name: string
      primitives[
        {
          extensions{
          }
          extras{
          }
          attributes{
          }
          indices: integer
          material: integer
          mode{
          }
          targets[
            {
            }
          ]
        }
      ]
      weights[number]
    }
  ]
  nodes[
    {
      extensions{
      }
      extras{
      }
      name: string
      camera: integer
      children[integer]
      skin: integer
      matrix[number]
      mesh: integer
      rotation[number]
      scale[number]
      translation[number]
      weights[number]
    }
  ]
  samplers[
    {
      extensions{
      }
      extras{
      }
      name: string
      magFilter{
      }
      minFilter{
      }
      wrapS{
      }
      wrapT{
      }
    }
  ]
  scene: integer
  scenes[
    {
      extensions{
      }
      extras{
      }
      name: string
      nodes[integer]
    }
  ]
  skins[
    {
      extensions{
      }
      extras{
      }
      name: string
      inverseBindMatrices: integer
      skeleton: integer
      joints[integer]
    }
  ]
  textures[
    {
      extensions{
      }
      extras{
      }
      name: string
      sampler: integer
      source: integer
    }
  ]
}
'''
```
