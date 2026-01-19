from enum import Enum
import re
from extensions.utils import choicify

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
    def bannerwriter_url_index(self) -> str:
        return COLOR_TO_BANNERWRITER_URL_INDEX[self]

    @property
    def planetminecraft_url_index(self) -> str:
        return COLOR_TO_PLANETMINECRAFT_URL_INDEX[self]

COLOR_CHOICES = choicify([c.pretty_name for c in Color])

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

COLOR_TO_BANNERWRITER_URL_INDEX = {
    Color.White: "0",
    Color.LightGray: "1",
    Color.Gray: "2",
    Color.Black: "3",
    Color.Yellow: "4",
    Color.Orange: "5",
    Color.Red: "6",
    Color.Brown: "7",
    Color.Lime: "8",
    Color.Green: "9",
    Color.LightBlue: "A",
    Color.Cyan: "B",
    Color.Blue: "C",
    Color.Pink: "D",
    Color.Magenta: "E",
    Color.Purple: "F",
}

COLOR_TO_PLANETMINECRAFT_URL_INDEX = {
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
    Flow = 41
    Guster = 42

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
    def bannerwriter_url_index(self) -> str:
        return PATTERN_TO_BANNERWRITER_URL_INDEX[self]

    @property
    def planetminecraft_url_index(self) -> str:
        return PATTERN_TO_PLANETMINECRAFT_URL_INDEX.get(self)

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
    Pattern.Snout: "pig",
    Pattern.Flow: "flw",
    Pattern.Guster: "gus",
}

PATTERN_TO_BANNERWRITER_URL_INDEX = {
    Pattern.Banner: ".",
    Pattern.Bordure: "G",
    Pattern.FieldMasoned: "H",
    Pattern.Roundel: "I",
    Pattern.CreeperCharge: "J",
    Pattern.Saltire: "K",
    Pattern.BordureIndented: "L",
    Pattern.PerBendSinister: "M",
    Pattern.PerBend: "N",
    Pattern.PerBendInverted: "O",
    Pattern.PerBendSinisterInverted: "P",
    Pattern.FlowerCharge: "Q",
    Pattern.Globe: "R",
    Pattern.Gradient: "S",
    Pattern.BaseGradient: "T",
    Pattern.PerFess: "U",
    Pattern.PerFessInverted: "V",
    Pattern.PerPale: "W",
    Pattern.PerPaleInverted: "X",
    Pattern.Thing: "Y",
    Pattern.Snout: "Z",
    Pattern.Lozenge: "a",
    Pattern.SkullCharge: "b",
    Pattern.Paly: "c",
    Pattern.BaseDexterCanton: "d",
    Pattern.BaseSinisterCanton: "e",
    Pattern.ChiefDexterCanton: "f",
    Pattern.ChiefSinisterCanton: "g",
    Pattern.Cross: "h",
    Pattern.Base: "i",
    Pattern.Pale: "j",
    Pattern.BendSinister: "k",
    Pattern.Bend: "l",
    Pattern.PaleDexter: "m",
    Pattern.Fess: "n",
    Pattern.PaleSinister: "o",
    Pattern.Chief: "p",
    Pattern.Chevron: "q",
    Pattern.InvertedChevron: "r",
    Pattern.BaseIndented: "s",
    Pattern.ChiefIndented: "t",
    Pattern.Flow: "u",
    Pattern.Guster: "v",
}

PATTERN_TO_PLANETMINECRAFT_URL_INDEX = {
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
    Pattern.BaseGradient: "C",
    Pattern.Flow: "H",
    Pattern.Guster: "I",
}

UNICODE_LOOKALIKES = {
    Pattern.Banner: "█",
    Pattern.Base: "▁",
    Pattern.Chief: "▔",
    Pattern.PaleDexter: "▏",
    Pattern.PaleSinister: "▕",
    Pattern.Fess: "-",
    Pattern.Pale: "|",
    Pattern.Bend: "\\\\",
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
    Pattern.BaseGradient: "⏶",
    Pattern.Flow: "𖦹",
    Pattern.Guster: "⏚"
}