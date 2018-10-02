
from typing import Dict, Any, List, Optional
from enum import Enum

class E_componentType(Enum):
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126

class E_type(Enum):
    SCALAR = "SCALAR"
    VEC2 = "VEC2"
    VEC3 = "VEC3"
    VEC4 = "VEC4"
    MAT2 = "MAT2"
    MAT3 = "MAT3"
    MAT4 = "MAT4"

class AccessorSparseIndices:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.bufferView: int = -1
        self.byteOffset: int = 0
        self.componentType: Optional[E_componentType] = None

class AccessorSparseValues:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.bufferView: int = -1
        self.byteOffset: int = 0

class AccessorSparse:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.count: int = -1
        self.indices: AccessorSparseIndices = AccessorSparseIndices()
        self.values: AccessorSparseValues = AccessorSparseValues()

class Accessor:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.bufferView: int = -1
        self.byteOffset: int = 0
        self.componentType: Optional[E_componentType] = None
        self.normalized: bool = False
        self.count: int = -1
        self.type: Optional[E_type] = None
        self.max: List[float] = []
        self.min: List[float] = []
        self.sparse: AccessorSparse = AccessorSparse()

class E_path(Enum):
    translation = "translation"
    rotation = "rotation"
    scale = "scale"
    weights = "weights"

class AnimationChannelTarget:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.node: int = -1
        self.path: Optional[E_path] = None

class AnimationChannel:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.sampler: int = -1
        self.target: AnimationChannelTarget = AnimationChannelTarget()

class E_interpolation(Enum):
    LINEAR = "LINEAR"
    STEP = "STEP"
    CUBICSPLINE = "CUBICSPLINE"

class AnimationSampler:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.input: int = -1
        self.interpolation: E_interpolation = E_interpolation("LINEAR")
        self.output: int = -1

class Animation:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.channels: List[AnimationChannel] = []
        self.samplers: List[AnimationSampler] = []

class Asset:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.copyright: str = ""
        self.generator: str = ""
        self.version: str = ""
        self.minVersion: str = ""

class Buffer:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.uri: str = ""
        self.byteLength: int = -1

class E_target(Enum):
    ARRAY_BUFFER = 34962
    ELEMENT_ARRAY_BUFFER = 34963

class BufferView:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.buffer: int = -1
        self.byteOffset: int = 0
        self.byteLength: int = -1
        self.byteStride: int = -1
        self.target: Optional[E_target] = None

class CameraOrthographic:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.xmag: float = float("nan")
        self.ymag: float = float("nan")
        self.zfar: float = float("nan")
        self.znear: float = float("nan")

class CameraPerspective:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.aspectRatio: float = float("nan")
        self.yfov: float = float("nan")
        self.zfar: float = float("nan")
        self.znear: float = float("nan")

class Camera:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.orthographic: CameraOrthographic = CameraOrthographic()
        self.perspective: CameraPerspective = CameraPerspective()
        self.type: Optional[E_type] = None

class E_mimeType(Enum):
    image_jpeg = "image/jpeg"
    image_png = "image/png"

class Image:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.uri: str = ""
        self.mimeType: Optional[E_mimeType] = None
        self.bufferView: int = -1

class TextureInfo:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.index: int = -1
        self.texCoord: int = 0

class MaterialPBRMetallicRoughness:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.baseColorFactor: List[float] = []
        self.baseColorTexture: TextureInfo = TextureInfo()
        self.metallicFactor: float = 1.0
        self.roughnessFactor: float = 1.0
        self.metallicRoughnessTexture: TextureInfo = TextureInfo()

class MaterialNormalTextureInfo:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.index: int = -1
        self.texCoord: int = 0
        self.scale: float = 1.0

class MaterialOcclusionTextureInfo:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.index: int = -1
        self.texCoord: int = 0
        self.strength: float = 1.0

class E_alphaMode(Enum):
    OPAQUE = "OPAQUE"
    MASK = "MASK"
    BLEND = "BLEND"

class Material:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.pbrMetallicRoughness: MaterialPBRMetallicRoughness = MaterialPBRMetallicRoughness()
        self.normalTexture: MaterialNormalTextureInfo = MaterialNormalTextureInfo()
        self.occlusionTexture: MaterialOcclusionTextureInfo = MaterialOcclusionTextureInfo()
        self.emissiveTexture: TextureInfo = TextureInfo()
        self.emissiveFactor: List[float] = []
        self.alphaMode: E_alphaMode = E_alphaMode("OPAQUE")
        self.alphaCutoff: float = 0.5
        self.doubleSided: bool = False

class E_mode(Enum):
    POINTS = 0
    LINES = 1
    LINE_LOOP = 2
    LINE_STRIP = 3
    TRIANGLES = 4
    TRIANGLE_STRIP = 5
    TRIANGLE_FAN = 6

class MeshPrimitive:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.attributes: Dict[str, int] = {}
        self.indices: int = -1
        self.material: int = -1
        self.mode: E_mode = E_mode(4)
        self.targets: List[Dict[str, int]] = []

class Mesh:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.primitives: List[MeshPrimitive] = []
        self.weights: List[float] = []

class Node:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.camera: int = -1
        self.children: List[int] = []
        self.skin: int = -1
        self.matrix: List[float] = []
        self.mesh: int = -1
        self.rotation: List[float] = []
        self.scale: List[float] = []
        self.translation: List[float] = []
        self.weights: List[float] = []

class E_magFilter(Enum):
    NEAREST = 9728
    LINEAR = 9729

class E_minFilter(Enum):
    NEAREST = 9728
    LINEAR = 9729
    NEAREST_MIPMAP_NEAREST = 9984
    LINEAR_MIPMAP_NEAREST = 9985
    NEAREST_MIPMAP_LINEAR = 9986
    LINEAR_MIPMAP_LINEAR = 9987

class E_wrapS(Enum):
    CLAMP_TO_EDGE = 33071
    MIRRORED_REPEAT = 33648
    REPEAT = 10497

class E_wrapT(Enum):
    CLAMP_TO_EDGE = 33071
    MIRRORED_REPEAT = 33648
    REPEAT = 10497

class Sampler:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.magFilter: Optional[E_magFilter] = None
        self.minFilter: Optional[E_minFilter] = None
        self.wrapS: E_wrapS = E_wrapS(10497)
        self.wrapT: E_wrapT = E_wrapT(10497)

class Scene:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.nodes: List[int] = []

class Skin:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.inverseBindMatrices: int = -1
        self.skeleton: int = -1
        self.joints: List[int] = []

class Texture:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.name: str = ""
        self.sampler: int = -1
        self.source: int = -1

class glTF:
    def __init__(self)->None:
        self.extensions: Dict[str, Any] = {}
        self.extras: Dict[str, Any] = {}
        self.extensionsUsed: List[str] = []
        self.extensionsRequired: List[str] = []
        self.accessors: List[Accessor] = []
        self.animations: List[Animation] = []
        self.asset: Asset = Asset()
        self.buffers: List[Buffer] = []
        self.bufferViews: List[BufferView] = []
        self.cameras: List[Camera] = []
        self.images: List[Image] = []
        self.materials: List[Material] = []
        self.meshes: List[Mesh] = []
        self.nodes: List[Node] = []
        self.samplers: List[Sampler] = []
        self.scene: int = -1
        self.scenes: List[Scene] = []
        self.skins: List[Skin] = []
        self.textures: List[Texture] = []
