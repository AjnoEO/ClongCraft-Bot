from json import JSONEncoder
from enum import Enum
from PIL import Image
from typing import List, Dict, Any
import re, sys, inspect

with Image.open("banners.png") as BANNER_SPRITESHEET: BANNER_SPRITESHEET.load()
SPRITES = []
for r in range(41):
    row = []
    for c in range(16):
        row.append(BANNER_SPRITESHEET.crop((c * 40, r * 40, c * 40 + 20, r * 40 + 40)))
    SPRITES.append(row)

class Direction(Enum):
    Up = 0
    Right = 1
    Down = 2
    Left = 3

class Color(Enum):
    White = 0
    Orange = 1
    Magenta = 2
    LightBlue = 3
    Yellow = 4
    Lime = 5
    Pink = 6
    Gray = 7
    LightGray = 8
    Cyan = 9
    Purple = 10
    Blue = 11
    Brown = 12
    Green = 13
    Red = 14
    Black = 15

    @property
    def pretty_name(self) -> str:
        return re.compile(r"([a-z])([A-Z])").sub(r"\1 \2", self.name)

    @property
    def unicode_index(self) -> int:
        return COLOR_TO_UNICODE_INDEX[self]

    @property
    def banner_url_index(self) -> str:
        return COLOR_TO_URL_INDEX[self]

COLOR_CHOICES = [c.pretty_name for c in Color]

COLOR_TO_UNICODE_INDEX = {
    Color.White: 0,
    Color.LightGray: 1,
    Color.Gray: 2,
    Color.Black: 3,
    Color.Yellow: 4,
    Color.Orange: 5,
    Color.Red: 6,
    Color.Brown: 7,
    Color.Lime: 8,
    Color.Green: 9,
    Color.LightBlue: 10,
    Color.Cyan: 11,
    Color.Blue: 12,
    Color.Pink: 13,
    Color.Magenta: 14,
    Color.Purple: 15
}

COLOR_TO_URL_INDEX = {
    Color.White: "g",
    Color.LightGray: "8",
    Color.Gray: "9",
    Color.Black: "1",
    Color.Yellow: "c",
    Color.Orange: "f",
    Color.Red: "2",
    Color.Brown: "4",
    Color.Lime: "b",
    Color.Green: "3",
    Color.LightBlue: "d",
    Color.Cyan: "7",
    Color.Blue: "5",
    Color.Pink: "a",
    Color.Magenta: "e",
    Color.Purple: "6"
}

class Pattern(Enum):
    Banner = 0
    Bordure = 1
    FieldMasoned = 2
    Roundel = 3
    CreeperCharge = 4
    Saltire = 5
    BordureIndented = 6
    PerBendSinister = 7
    PerBend = 8
    PerBendInverted = 9
    PerBendSinisterInverted = 10
    FlowerCharge = 11
    Globe = 12
    Gradient = 13
    BaseGradient = 14
    PerFess = 15
    PerFessInverted = 16
    PerPale = 17
    PerPaleInverted = 18
    Thing = 19
    Snout = 20
    Lozenge = 21
    SkullCharge = 22
    Paly = 23
    BaseDexterCanton = 24
    BaseSinisterCanton = 25
    ChiefDexterCanton = 26
    ChiefSinisterCanton = 27
    Cross = 28
    Base = 29
    Pale = 30
    BendSinister = 31
    Bend = 32
    PaleDexter = 33
    Fess = 34
    PaleSinister = 35
    Chief = 36
    Chevron = 37
    InvertedChevron = 38
    BaseIndented = 39
    ChiefIndented = 40

    @property
    def pretty_name_no_char(self) -> str:
        return re.compile(r"([a-z])([A-Z])").sub(r"\1 \2", self.name)

    @property
    def pretty_name(self) -> str:
        return self.pretty_name_no_char + " (" + UNICODE_LOOKALIKES[self] + ")"

    @property
    def data_value(self) -> str:
        return PATTERN_TO_DATA_VALUE[self]

    @property
    def banner_url_index(self) -> str:
        return PATTERN_TO_URL_INDEX.get(self)

async def pattern_autocomplete(option, interaction):
    output = []
    input_data = option.value.lower()
    for p in Pattern:
        if p != Pattern.Banner and input_data in p.pretty_name.lower(): output.append(p.pretty_name)
    return sorted(output, key = str.lower)[:25]

PATTERN_TO_DATA_VALUE = {
    Pattern.Banner: "b",
    Pattern.Base: "bs",
    Pattern.Chief: "ts",
    Pattern.PaleDexter: "ls",
    Pattern.PaleSinister: "rs",
    Pattern.Pale: "cs",
    Pattern.Fess: "ms",
    Pattern.Bend: "drs",
    Pattern.BendSinister: "dls",
    Pattern.Paly: "ss",
    Pattern.Saltire: "cr",
    Pattern.Cross: "sc",
    Pattern.PerBendSinister: "ld",
    Pattern.PerBend: "rud",
    Pattern.PerBendInverted: "lud",
    Pattern.PerBendSinisterInverted: "rd",
    Pattern.PerPale: "vh",
    Pattern.PerPaleInverted: "vhr",
    Pattern.PerFess: "hh",
    Pattern.PerFessInverted: "hhb",
    Pattern.BaseDexterCanton: "bl",
    Pattern.BaseSinisterCanton: "br",
    Pattern.ChiefDexterCanton: "tl",
    Pattern.ChiefSinisterCanton: "tr",
    Pattern.Chevron: "bt",
    Pattern.InvertedChevron: "tt",
    Pattern.BaseIndented: "bts",
    Pattern.ChiefIndented: "tts",
    Pattern.Roundel: "mc",
    Pattern.Lozenge: "mr",
    Pattern.Bordure: "bo",
    Pattern.BordureIndented: "cbo",
    Pattern.FieldMasoned: "bri",
    Pattern.Gradient: "gra",
    Pattern.BaseGradient: "gru",
    Pattern.CreeperCharge: "cre",
    Pattern.SkullCharge: "sku",
    Pattern.FlowerCharge: "flo",
    Pattern.Thing: "moj",
    Pattern.Globe: "glb",
    Pattern.Snout: "pig"
}

PATTERN_TO_URL_INDEX = {
    Pattern.Base: "o",
    Pattern.Chief: "v",
    Pattern.PaleDexter: "s",
    Pattern.PaleSinister: "u",
    Pattern.Fess: "t",
    Pattern.Pale: "p",
    Pattern.Bend: "r",
    Pattern.BendSinister: "q",
    Pattern.Saltire: "7",
    Pattern.Paly: "i",
    Pattern.Cross: "n",
    Pattern.PerBend: "a",
    Pattern.PerBendSinister: "9",
    Pattern.PerBendInverted: "A",
    Pattern.PerBendSinisterInverted: "B",
    Pattern.PerPale: "e",
    Pattern.PerPaleInverted: "E",
    Pattern.PerFess: "d",
    Pattern.PerFessInverted: "D",
    Pattern.BaseDexterCanton: "j",
    Pattern.BaseSinisterCanton: "k",
    Pattern.ChiefDexterCanton: "l",
    Pattern.ChiefSinisterCanton: "m",
    Pattern.Chevron: "y",
    Pattern.InvertedChevron: "z",
    Pattern.BaseIndented: "w",
    Pattern.ChiefIndented: "x",
    Pattern.Roundel: "5",
    Pattern.Lozenge: "g",
    Pattern.Bordure: "3",
    Pattern.BordureIndented: "8",
    Pattern.FieldMasoned: "4",
    Pattern.CreeperCharge: "6",
    Pattern.SkullCharge: "h",
    Pattern.FlowerCharge: "b",
    Pattern.Thing: "f",
    Pattern.Globe: "F",
    Pattern.Snout: "G",
    Pattern.Gradient: "c",
    Pattern.BaseGradient: "C"
}

UNICODE_LOOKALIKES = {
    Pattern.Banner: "█",
    Pattern.Base: "▁",
    Pattern.Chief: "▔",
    Pattern.PaleDexter: "▏",
    Pattern.PaleSinister: "▕",
    Pattern.Fess: "-",
    Pattern.Pale: "|",
    Pattern.Bend: "\\",
    Pattern.BendSinister: "/",
    Pattern.Saltire: "X",
    Pattern.Paly: "ꘈ",
    Pattern.Cross: "+",
    Pattern.PerBend: "◥",
    Pattern.PerBendSinister: "◤",
    Pattern.PerBendInverted: "◣",
    Pattern.PerBendSinisterInverted: "◢",
    Pattern.PerPale: "▌",
    Pattern.PerPaleInverted: "▐",
    Pattern.PerFess: "▀",
    Pattern.PerFessInverted: "▄",
    Pattern.BaseDexterCanton: "▖",
    Pattern.BaseSinisterCanton: "▗",
    Pattern.ChiefDexterCanton: "▘",
    Pattern.ChiefSinisterCanton: "▝",
    Pattern.Chevron: "▲",
    Pattern.InvertedChevron: "▼",
    Pattern.BaseIndented: "⏟",
    Pattern.ChiefIndented: "⏞",
    Pattern.Roundel: "●",
    Pattern.Lozenge: "◆",
    Pattern.Bordure: "◻",
    Pattern.BordureIndented: "▩",
    Pattern.FieldMasoned: "▤",
    Pattern.CreeperCharge: "⍨",
    Pattern.SkullCharge: "⍚",
    Pattern.FlowerCharge: "⌾",
    Pattern.Thing: "ᕧ",
    Pattern.Globe: "⬡",
    Pattern.Snout: "🀹",
    Pattern.Gradient: "⏷",
    Pattern.BaseGradient: "⏶"
}

class Layer:
    def __init__(self, color: Color, pattern: Pattern):
        self.__color = color
        self.__pattern = pattern

    @property
    def color(self) -> Color: return self.__color

    @property
    def pattern(self) -> Pattern: return self.__pattern

    def __repr__(self) -> str: return f"Layer[{self.color.name} {self.pattern.name}]"

    @property
    def character(self) -> str:
        return chr(0xE000 + 0x100 * self.color.unicode_index + int(str(self.pattern.value), base = 16))

    @property
    def base_text(self) -> str:
        if self.pattern == Pattern.Banner: return ""
        if self.color == Color.White: return "\uE300\U000CFFF7"
        return "\uE000\U000CFFF7"

    @property
    def sprite(self) -> Image:
        return SPRITES[self.pattern.value][self.color.unicode_index]

    @property
    def banner_code(self) -> str:
        return self.pattern.data_value + str(self.color.value)

    @property
    def banner_url_part(self) -> str:
        return self.color.banner_url_index + self.pattern.banner_url_index

    @classmethod
    def from_character(cls, char: str) -> "Layer":
        value = ord(char)
        assert 0xE000 <= value < 0xF000, f"Character U+{hex(value)[2:].zfill(4)} is out of range"
        value -= 0xE000
        pattern_index = int(hex(value % 0x100)[2:])
        for pattern in Pattern:
            if pattern.value == pattern_index: break
        else: raise ValueError(f"No pattern indexed with {pattern_index}")
        color_index = value // 0x100
        for color in Color:
            if color.unicode_index == color_index: break
        else: raise ValueError("What the heck? HOW?? This shouldn't be reachable!")
        return cls(color, pattern)

    @classmethod
    def from_banner_code_part(cls, part: str) -> "Layer":
        r = re.compile(r"([a-z]+)(\d+)")
        match = r.fullmatch(part)
        assert match, f"Invalid code part: {part}"
        pattern_part, color_part = match.groups()
        for pattern in Pattern:
            if pattern.data_value == pattern_part: break
        else: raise ValueError(f"Invalid pattern: {pattern_part}")
        for color in Color:
            if str(color.value) == color_part: break
        else: raise ValueError(f"Invalid color: {color_part}")
        return Layer(color, pattern)

    @classmethod
    def from_banner_url_part(cls, part: str) -> "Layer":
        assert len(part) == 2, f"Invalid URL part: {part}"
        color_char, pattern_char = part
        for color in Color:
            if color.banner_url_index == color_char: break
        else: raise ValueError(f"Invalid color: {color_char}")
        for pattern in Pattern:
            if pattern.banner_url_index == pattern_char: break
        else: raise ValueError(f"Invalid pattern: {pattern_char}")
        return Layer(color, pattern)

    def copy(self) -> "Layer":
        return Layer(self.color, self.pattern)

    def set(self, other: "Layer") -> None:
        self.__color = other.color
        self.__pattern = other.pattern

class Banner:
    def __init__(self, base_color: Color, layers: List[Layer]):
        self.__base_color = base_color
        self.layers = layers

    @property
    def base_color(self) -> Color: return self.__base_color

    @property
    def all_layers(self) -> List[Layer]: return [Layer(self.base_color, Pattern.Banner)] + self.layers

    def __repr__(self) -> str: return f"Banner[{', '.join(repr(layer) for layer in self.all_layers)}]"

    @property
    def image(self) -> Image:
        output = Image.new("RGBA", (20, 40))
        for layer in self.all_layers:
            output.alpha_composite(layer.sprite)
        return output

    @property
    def text(self) -> str:
        return "\U000CFFF7".join(layer.character for layer in self.all_layers)

    @property
    def banner_code(self) -> str:
        return "".join(layer.banner_code for layer in self.all_layers)

    @property
    def banner_url(self) -> str:
        return "https://www.planetminecraft.com/banner/?b=" + \
               self.base_color.banner_url_index + "".join(layer.banner_url_part for layer in self.layers)

    @classmethod
    def from_text(cls, text: str) -> "Banner":
        assert set(text) <= {"\U000CFFF7"} | set(chr(c) for c in range(0xE000, 0xF000)), "Please use banner text"
        assert set(text[1::2]) == {"\U000CFFF7"}, "Only one banner should be provided"
        all_layers = [Layer.from_character(c) for c in text[::2]]
        assert all_layers[0].pattern == Pattern.Banner, "The banner should start with a full pattern"
        return cls(all_layers[0].color, all_layers[1:])

    @classmethod
    def from_banner_code(cls, banner_code: str) -> "Banner":
        assert re.compile(r"[a-z\d]+").fullmatch(banner_code), f"Invalid banner code: {banner_code}"
        parts = re.compile(r"([a-z]+\d+)").sub(r"\1,", banner_code).split(",")[:-1]
        all_layers = [Layer.from_banner_code_part(part) for part in parts]
        assert all_layers, f"Invalid banner code: {banner_code}"
        assert all_layers[0].pattern == Pattern.Banner, "The banner should start with a full pattern"
        return cls(all_layers[0].color, all_layers[1:])

    @classmethod
    def from_banner_url(cls, banner_url: str) -> "Banner":
        assert banner_url.startswith("https://www.planetminecraft.com/banner/?b="), \
            f"Non-banner maker URL: {banner_url}"
        banner_url = banner_url[42:]
        for base_color in Color:
            if base_color.banner_url_index == banner_url[0]: break
        else: raise ValueError(f"Invalid color: {banner_url[0]}")
        layer_parts = [banner_url[x:x+2] for x in range(1, len(banner_url), 2)]
        layers = [Layer.from_banner_url_part(layer_part) for layer_part in layer_parts]
        return cls(base_color, layers)

    @property
    def description(self) -> str:
        layer_text = "\n".join(
            f"{i}. {layer.color.pretty_name} {layer.pattern.pretty_name} {layer.base_text}{layer.character}"
            for i, layer in enumerate(self.all_layers)
        )
        return f"""Text: {self.text}
Copyable: ```
{self.text}
```
Banner code: `{self.banner_code}`
URL: {self.banner_url}
Layers:
{layer_text}"""

    def copy(self) -> "Banner":
        return Banner(self.base_color, [layer.copy() for layer in self.layers])

class BannerSet:
    def __init__(self, writing_direction: Direction, newline_direction: Direction, space_char: str, newline_char: str):
        self.banners: Dict[str, Banner] = {}
        self.__writing_direction = writing_direction
        self.__newline_direction = newline_direction
        self.__space_char = space_char
        self.__newline_char = newline_char

    @property
    def writing_direction(self): return self.__writing_direction

    @property
    def newline_direction(self): return self.__newline_direction

    @property
    def space_char(self): return self.__space_char

    @property
    def newline_char(self): return self.__newline_char

class BannerJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return {"__type": o.__class__.__name__, "value": o.value}
        elif isinstance(o, Layer):
            return {"__type": "Layer", "args": [o.color, o.pattern]}
        elif isinstance(o, Banner):
            return {"__type": "Banner", "code": o.banner_code}
        elif isinstance(o, BannerSet):
            return {
                "__type": "BannerSet",
                "banners": o.banners,
                "args": [o.writing_direction, o.newline_direction, o.space_char, o.newline_char]
            }
        else:
            return super().default(o)

cls_members = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))

def banner_json_decode_hook(json_object):
    if type(json_object) in cls_members.values(): return json_object
    if "__type" in json_object:
        this_class = cls_members[json_object["__type"]]
        if issubclass(this_class, Enum):
            for item in this_class:
                if item.value == json_object["value"]:
                    return item
        elif this_class == Banner:
            return Banner.from_banner_code(json_object["code"])
        else:
            args = [banner_json_decode_hook(x) for x in json_object["args"]]
            if this_class is BannerSet:
                result = BannerSet(*args)
                result.banners = banner_json_decode_hook(json_object["banners"])
                return result
            else:
                return this_class(*args)
    return json_object