from .banner_enums import *
import hikari
import lightbulb
import inspect
from json import JSONEncoder
from PIL import Image
import re
from .splitting import SplitMode
import sys
from typing import List, Dict, Any
from .utils import urlize, save_temporarily

PATTERNS_COUNT = 42
COLORS_COUNT = 16

with Image.open("banners.png") as BANNER_SPRITESHEET: BANNER_SPRITESHEET.load()
SPRITES = []
for r in range(PATTERNS_COUNT+1):
    row = []
    for c in range(COLORS_COUNT):
        row.append(BANNER_SPRITESHEET.crop((c * 40, r * 40, c * 40 + 20, r * 40 + 40)))
    SPRITES.append(row)

async def pattern_autocomplete(ctx: lightbulb.AutocompleteContext[str]) -> None:
    output = []
    input_data = ctx.focused.value.lower()
    for p in Pattern:
        if p != Pattern.Banner and input_data in p.pretty_name.lower(): output.append(p.pretty_name)
    await ctx.respond(sorted(output, key = str.lower)[:25])
    return

class Layer:
    def __init__(self, color: Color, pattern: Pattern):
        self.color = color
        self.pattern = pattern

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
    def pretty_name(self) -> str: return f"{self.color.pretty_name} {self.pattern.pretty_name} {self.base_text}{self.character}"

    @property
    def sprite(self) -> Image.Image:
        return SPRITES[self.pattern.value][self.color.unicode_index]

    @property
    def banner_code(self) -> str:
        return self.pattern.data_value + str(self.color.value)

    @property
    def planetminecraft_url_part(self) -> str:
        return self.color.planetminecraft_url_index + self.pattern.planetminecraft_url_index

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
    def from_planetminecraft_url_part(cls, part: str) -> "Layer":
        assert len(part) == 2, f"Invalid URL part: {part}"
        color_char, pattern_char = part
        for color in Color:
            if color.planetminecraft_url_index == color_char: break
        else: raise ValueError(f"Invalid color: {color_char}")
        for pattern in Pattern:
            if pattern.planetminecraft_url_index == pattern_char: break
        else: raise ValueError(f"Invalid pattern: {pattern_char}")
        return Layer(color, pattern)

    def copy(self) -> "Layer":
        return Layer(self.color, self.pattern)

    def set(self, other: "Layer") -> None:
        self.__color = other.color
        self.__pattern = other.pattern

class Banner:
    def __init__(self, base_color: Color, layers: List[Layer] = []):
        self.base_color = base_color
        self.layers = layers

    @property
    def all_layers(self) -> List[Layer]: return [Layer(self.base_color, Pattern.Banner)] + self.layers

    def __repr__(self) -> str: return f"Banner[{', '.join(repr(layer) for layer in self.all_layers)}]"

    @property
    def image(self) -> Image.Image:
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
    def planetminecraft_url(self) -> str:
        return "planetminecraft.com/banner/?b=" + \
            self.base_color.planetminecraft_url_index + "".join(layer.planetminecraft_url_part for layer in self.layers)

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
    def from_bannerwriter_url(cls, bannerwriter_url: str) -> "Banner":
        assert bannerwriter_url.startswith("https://banner-writer.web.app/image/"), \
            f"Not a bannerwriter URL: {bannerwriter_url}"
        assert len(bannerwriter_url) >= 37 and bannerwriter_url[36] == "L" or bannerwriter_url[36] == "R", \
            f"Bannerwriter URL didn't have a direction control character: {bannerwriter_url[36]}"
        assert bannerwriter_url.endswith(".png"), \
            f"Bannerwriter URL didn't end with a .png extension: {bannerwriter_url}"
        bannerwriter_url = bannerwriter_url[37:-4]
        current_color = Color.White # Color is changed only when required in this URL type. Default is white.
        layers = []
        for char in bannerwriter_url:
            for color in Color:
                if color.bannerwriter_url_index == char:
                    current_color = color
                    break
            else:
                for pattern in Pattern:
                    if pattern.bannerwriter_url_index == char:
                        layers.append(Layer(current_color, pattern))
                        break
                else:
                    if char == "_" or char == "~":
                        raise ValueError(f"Bannerwriter URL contained space/newline: {bannerwriter_url}")
                    raise ValueError(f"Invalid character detected: {char}")
        assert len(layers) > 0, \
            f"Banner from Bannerwriter URL was empty: {bannerwriter_url}"
        background = layers.pop(0)
        assert background.pattern == Pattern.Banner, \
            f"Banner from Bannerwriter URL didn't start with a background: {bannerwriter_url}"
        for layer in layers:
            assert layer.pattern != Pattern.Banner, \
                f"Bannerwriter URL contained multiple banners: {bannerwriter_url}"
        return cls(background.color, layers)
    
    @classmethod
    def from_bannerwriter_url_multi(cls, bannerwriter_url: str) -> List[List["Banner"]]:
        assert bannerwriter_url.startswith("https://banner-writer.web.app/image/"), \
            f"Not a bannerwriter URL: {bannerwriter_url}"
        assert len(bannerwriter_url) >= 37 and bannerwriter_url[36] == "L" or bannerwriter_url[36] == "R", \
            f"Bannerwriter URL didn't have a direction control character: {bannerwriter_url[36]}"
        assert bannerwriter_url.endswith(".png"), \
            f"Bannerwriter URL didn't end with a .png extension: {bannerwriter_url}"
        bannerwriter_url = bannerwriter_url[37:-4]
        current_color = Color.White # Color is changed only when required in this URL type. Default is white.
        lines: List[List[Banner | None]] = []
        line: List[Banner | None] = []
        banner = None

        for char in bannerwriter_url:
            for color in Color:
                if color.bannerwriter_url_index == char:
                    current_color = color
                    break
            else:
                if char == ".":
                    if banner:
                        line.append(banner)
                    banner = Banner(base_color=current_color, layers=[])
                for pattern in Pattern:
                    if pattern.bannerwriter_url_index == char:
                        if not banner:
                            raise ValueError("Banner had no background")
                        banner.layers.append(Layer(current_color, pattern))
                        break
                else:
                    if char == "_":
                        if banner:
                            line.append(banner)
                        banner = None
                    elif char == "~":
                        if banner:
                            line.append(banner)
                        banner = None
                        lines.append(line)
                        line = []
                    else:
                        raise ValueError(f"Invalid character detected: {char}")
        if banner:
            line.append(banner)
        lines.append(line)
        return lines
    
    @classmethod
    def from_planetminecraft_url(cls, planetminecraft_url: str) -> "Banner":
        assert planetminecraft_url.startswith("https://www.planetminecraft.com/banner/?b="), \
            f"Not a planetminecraft URL: {planetminecraft_url}"
        planetminecraft_url = planetminecraft_url[42:]
        for base_color in Color:
            if base_color.planetminecraft_url_index == planetminecraft_url[0]: break
        else: raise ValueError(f"Invalid color: {planetminecraft_url[0]}")
        layer_parts = [planetminecraft_url[x:x+2] for x in range(1, len(planetminecraft_url), 2)]
        layers = [Layer.from_planetminecraft_url_part(layer_part) for layer_part in layer_parts]
        return cls(base_color, layers)
    
    @classmethod
    def from_banner_url(cls, url: str) -> "Banner":
        if url.startswith("https://banner-writer.web.app/image/"):
            return cls.from_bannerwriter_url(url)
        elif url.startswith("https://www.planetminecraft.com/banner/?b="):
            return cls.from_planetminecraft_url(url)
        else:
            raise ValueError(f"Unrecognized URL: {url}")
    
    @property
    def layers_description(self) -> str:
        return "\n".join(
            f"{i}. {layer.pretty_name}" for i, layer in enumerate(self.all_layers, start=1)
        )

    @property
    def description(self) -> str:
        return f"""Text: {self.text}
Copyable: ```
{self.text}
```
Banner code: `{self.banner_code}`
URL: {urlize(self.planetminecraft_url)}"""
    
    def as_components(self, img_path: str, selected: int | None = None) -> list[hikari.api.ComponentBuilder]:
        return [
            hikari.impl.TextDisplayComponentBuilder(content=self.description),
            hikari.impl.SectionComponentBuilder(
                accessory=hikari.impl.InteractiveButtonBuilder(
                    style=hikari.ButtonStyle.PRIMARY if selected == 0 else hikari.ButtonStyle.SECONDARY,
                    label="↑" if selected else "⠿",
                    custom_id="banner_unselect_0" if selected == 0 else "banner_select_0",
                    is_disabled=bool(selected)
                ),
                components=[
                    hikari.impl.TextDisplayComponentBuilder(content=f"1. {self.all_layers[0].pretty_name}"),
                ]
            ),
            *(hikari.impl.SectionComponentBuilder(
                accessory=hikari.impl.InteractiveButtonBuilder(
                    style=hikari.ButtonStyle.PRIMARY if selected == i else hikari.ButtonStyle.SECONDARY,
                    label="⠿" if selected is None or selected == i else "↑" if selected > i else "↓",
                    custom_id=
                        f"banner_unselect_{i}" if selected == i else
                        f"banner_select_{i}" if selected is None else
                        f"banner_move_{selected}_{i}",
                    is_disabled=(selected==0)
                ),
                components=[
                    hikari.impl.TextDisplayComponentBuilder(content=f"{i+1}. {layer.pretty_name}"),
                ]
            ) for i, layer in enumerate(self.layers, start=1)),
            hikari.impl.MediaGalleryComponentBuilder(
                items=[
                    hikari.impl.MediaGalleryItemBuilder(
                        media=img_path,
                    ),
                ]
            ),
            hikari.impl.MessageActionRowBuilder(
                components=[
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Change Color",
                        emoji="🖌️",
                        custom_id=f"banner_edit_color_{selected}",
                        is_disabled=selected is None,
                    ),
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Change Pattern",
                        emoji="⚜️",
                        custom_id=f"banner_edit_pattern_{selected}",
                        is_disabled=not selected,
                    ),
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Remove",
                        emoji="🗑️",
                        custom_id=f"banner_remove_{selected}",
                        is_disabled=not selected,
                    ),
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Add Pattern" if selected is None else "Insert After",
                        emoji="➕",
                        custom_id="banner_add" if selected is None else f"banner_add_{selected}",
                    ),
                ]
            ),
            hikari.impl.MessageActionRowBuilder(
                components=[
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="Clear Design",
                        emoji="❌",
                        custom_id="banner_clear",
                    ),
                    hikari.impl.InteractiveButtonBuilder(
                        style=hikari.ButtonStyle.SECONDARY,
                        label="New Banner",
                        emoji="✨",
                        custom_id="banner_new",
                    ),
                ]
            ),
            hikari.impl.TextDisplayComponentBuilder(content="-# Save the design using `/save`")
        ]

    def copy(self) -> "Banner":
        return Banner(self.base_color, [layer.copy() for layer in self.layers])

async def __show_callback(path, ctx: lightbulb.Context, banner: Banner, for_everyone: bool, editable: bool):
    if editable:
        await ctx.respond(
            components = banner.as_components(path),
            ephemeral = not for_everyone
        )
    else:
        await ctx.respond(
            banner.description + "\n" + banner.layers_description,
            attachment = hikari.File(path),
            ephemeral = not for_everyone
        )

async def respond_with_banner(ctx, banner: Banner, for_everyone = False, editable = True):
	await save_temporarily(__show_callback, banner.image.resize((80, 160), Image.Resampling.NEAREST),
						   ctx, banner, for_everyone, editable)

async def __edit_callback(path, interaction: hikari.ComponentInteraction, banner: Banner, selected: int | None):
    await interaction.edit_initial_response(components = banner.as_components(path, selected))

async def edit_for_banner(interaction: hikari.ComponentInteraction, banner: Banner, selected: int | None = None):
    await save_temporarily(__edit_callback, banner.image.resize((80, 160), Image.Resampling.NEAREST),
						   interaction, banner, selected)

async def __edit_color_callback(path, interaction: hikari.ComponentInteraction, description: str, button_prefix: str,
                                selected: Color | None, final_buttons: list[dict[str]]):
    await interaction.edit_initial_response(
        components = Color.as_components(description, path, button_prefix, selected, final_buttons)
    )

async def edit_for_color(interaction: hikari.ComponentInteraction, banner: Banner | None, description: str,
                         button_prefix: str, selected: Color | None, final_buttons: list[dict[str]]):
    if banner:
        await save_temporarily(__edit_color_callback,
                               banner.image.resize((80, 160), Image.Resampling.NEAREST).crop((-40, 0, 120, 160)),
                               interaction, description, button_prefix, selected, final_buttons)
    else:
        await __edit_color_callback(None, interaction, description, button_prefix, selected, final_buttons)

async def __edit_pattern_callback(path, interaction: hikari.ComponentInteraction, description: str, button_prefix: str,
                                  selected: Pattern | None, final_buttons: list[dict[str]], page_no: int | None):
    await interaction.edit_initial_response(
        components = Pattern.as_components(description, path, button_prefix, selected, final_buttons, page_no)
    )

async def edit_for_pattern(interaction: hikari.ComponentInteraction, banner: Banner, description: str, button_prefix: str,
                           selected: Pattern | None, final_buttons: list[dict[str]], page_no: int | None):
    if banner:
        await save_temporarily(__edit_pattern_callback,
                               banner.image.resize((80, 160), Image.Resampling.NEAREST).crop((-40, 0, 120, 160)),
                               interaction, description, button_prefix, selected, final_buttons, page_no)
    else:
        await __edit_pattern_callback(None, interaction, description, button_prefix, selected, final_buttons, page_no)

class BannerSet:
    def __init__(self, writing_direction: Direction, newline_direction: Direction, space_char: str, newline_char: str,
                 split_mode: SplitMode):
        self.banners: Dict[str, Banner] = {}
        self.__writing_direction = writing_direction
        self.__newline_direction = newline_direction
        self.__space_char = space_char
        self.__newline_char = newline_char
        self.__split_mode = split_mode

    @property
    def writing_direction(self): return self.__writing_direction

    @property
    def newline_direction(self): return self.__newline_direction

    @property
    def space_char(self): return self.__space_char

    @property
    def newline_char(self): return self.__newline_char

    @property
    def split_mode(self): return self.__split_mode

class BannerJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, SplitMode):
            return list(SplitMode).index(o)
        elif isinstance(o, Enum):
            return {"__type": o.__class__.__name__, "value": o.value}
        elif isinstance(o, Layer):
            return {"__type": "Layer", "args": [o.color, o.pattern]}
        elif isinstance(o, Banner):
            return {"__type": "Banner", "code": o.banner_code}
        elif isinstance(o, BannerSet):
            return {
                "__type": "BannerSet",
                "banners": o.banners,
                "args": [o.writing_direction, o.newline_direction, o.space_char, o.newline_char, o.split_mode]
            }
        else:
            return super().default(o)

cls_members = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))

def banner_json_decode_hook(json_object):
    if type(json_object) in cls_members.values(): return json_object
    if hasattr(json_object, "__iter__") and "__type" in json_object:
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
    elif isinstance(json_object, int):
        return list(SplitMode)[json_object]
    return json_object

def generate_bannerwriter_url(lines: List[List[Banner | None]], direction: Direction, newline_dir: Direction) -> str:
    output = "banner-writer.web.app/?writing="
    if direction == Direction.Down or direction == Direction.Up:
        return "`Banner writer does not currently support vertical writing direction`"
    if newline_dir != Direction.Down and len(lines) > 1:
        return "`Banner writer does not currently support newline direction Up`"
    if direction == Direction.Left:
        output += "L"
    if direction == Direction.Right:
        output += "R"

    color = Color.White
    for i,line in enumerate(lines):
        if i != 0:
            output += "~"
        for banner in reversed(line) if direction == Direction.Left else line:
            if banner == None:
                output += "_"
                continue
            for layer in banner.all_layers:
                if color != layer.color:
                    color = layer.color
                    output += COLOR_TO_BANNERWRITER_URL_INDEX[color]
                output += PATTERN_TO_BANNERWRITER_URL_INDEX[layer.pattern]
    return output

def generate_space_char(distance: int) -> str:
    return chr(0xD0000 + distance)

def optimize_banners_for_anvil(lines: List[List[Banner | None]], direction: Direction) -> tuple[str, int]:
    if direction == Direction.Down or direction == Direction.Up:
        return ("Anvil-optimized text does not support vertical writing direction", 0)

    flattened = lines.pop(0)
    for line in lines:
        # This will just treat newlines as spaces, since Anvils cannot have multiple lines.
        flattened += [None]
        flattened += line
    if direction == Direction.Left:
        flattened.reverse()

    line_layers = [(banner.all_layers if banner != None else []) for banner in flattened]

    # Optimization: If a small banner is in between two large banners, it is faster to repeat its layers
    # than to move forward by a space of only one banner. (Spaces are 2 chars, layers are only 1)
    for i in range(len(line_layers) - 2):
        left, middle, right = line_layers[i : i + 3]
        minimum = min(len(left), len(right))
        if 0 < len(middle) < minimum:
            for _ in range(minimum - len(middle)):
                middle.insert(0, middle[0])

    output = ""
    position = 0
    max_layers = max(len(layers) for layers in line_layers)
    length = 0
    # Build all banners in parallel, one layer at a time
    for i in range(max_layers):
        for pos,layers in enumerate(line_layers):
            if len(layers) > i:
                # Make sure you are at the right position before typing the next character
                if position != pos:
                    output += generate_space_char(9 * (pos - position))
                    position = pos
                    length += 2
                output += layers[i].character
                position += 1
                length += 1

    return (output, length)

# Limitation: This can currently only handle LTR or RTL writing directions. This is because
# item names in Minecraft do not support newlines, and so anvil-optimized text cannot be vertical.
def writing_description(lines, direction: Direction, newline_dir: Direction) -> str:
    bannerwriter_url = generate_bannerwriter_url(lines, direction, newline_dir)
    url = urlize(bannerwriter_url)
    (anvil, length) = optimize_banners_for_anvil(lines, direction)
    return \
f"""
Anvil-optimized text: `{anvil}`
URL: {url}
""" \
if length == 0 else \
f"""
Anvil-optimized text ({length}/50 characters):
```
{anvil}
```
URL: {url}
""" if length + len(url) <= 1850 else \
f"""
Anvil-optimized text ({length}/50 characters):
```
{anvil}
```
URL: [banner-writer.web.app/?writing=...](<https://{bannerwriter_url}>)
""" if length + len(bannerwriter_url) <= 1850 else \
f"""
Anvil-optimized text ({length}/50 characters):
```
{anvil}
```
(The banner URL is too long to be displayed)
""" if length <= 1850 else \
"The anvil-optimized text is too long to be displayed"