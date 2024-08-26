import hikari, lightbulb, os, json
from json import JSONDecoder
from configparser import ConfigParser
from banner import *
from utils import *
from typing import Dict, List, Optional
from PIL import Image, ImageDraw
from splitting import SplitMode

if os.path.exists("config.ini"):
    config = ConfigParser()
    config.read("config.ini")
else:
    raise FileExistsError("config.ini is missing.\n"
                          "If you cloned or pulled the git repo, "
                          "make sure to copy example.config.ini, "
                          "name it config.ini and edit for your needs.")


banner_designs: Dict[int, Banner] = {}
banner_sets: Dict[int, Dict[str, BannerSet]] = {}
last_used: Dict[int, str] = {}

if os.path.exists("data.json"):
    with open("data.json", encoding="utf-8") as f:
        data = JSONDecoder(object_hook = banner_json_decode_hook).decode(f.read())
    banner_designs = {int(k): v for k, v in data["designs"].items()}
    banner_sets = {int(k): v for k, v in data["sets"].items()}
    last_used = {int(k): v for k, v in data["last_used"].items()}

def save_banner_data():
    with open("data.json", "w") as f:
        json.dump({
            "designs": banner_designs,
            "sets": banner_sets,
            "last_used": last_used
        }, f, cls = BannerJSONEncoder, indent = 4)

async def layer_autocomplete(ctx: lightbulb.AutocompleteContext[str]) -> None:
    banner = banner_designs.get(ctx.interaction.user.id)
    if not banner:
        await ctx.respond([])
        return
    layers = [f"{i+1}. {layer.color.pretty_name} {layer.pattern.pretty_name}" for i, layer in enumerate(banner.layers)]
    input_data = ctx.focused.value.lower()
    await ctx.respond([layer for layer in layers if input_data in layer.lower()])
    return

def layer_to_index(ctx: lightbulb.Context, layer: str) -> Optional[int]:
    banner = banner_designs.get(ctx.user.id)
    if not banner: return None
    if not layer: return None
    layers = [f"{i+1}. {this_layer.color.pretty_name} {this_layer.pattern.pretty_name}"
              for i, this_layer in enumerate(banner.layers)]
    for i, possible_layer in enumerate(layers):
        if layer.lower() in possible_layer.lower(): return i + 1

def number_of_columns_for(number_of_banners):
    if number_of_banners <= 5: return number_of_banners
    if number_of_banners <= 30: return 6
    if number_of_banners <= 42: return 7
    if number_of_banners <= 56: return 8
    return 9

def get_working_set(user_id: int, set: str, update_last_used: bool = True) -> tuple[BannerSet, str]:
    banner_set_name = set or last_used.get(user_id)
    assert banner_set_name, "You must have a banner set"
    banner_sets.setdefault(user_id, {})
    assert banner_set_name in banner_sets[user_id], f"Banner set {banner_set_name} does not exist"
    if update_last_used:
        last_used[user_id] = banner_set_name
    return banner_sets[user_id][banner_set_name], banner_set_name

bot = hikari.GatewayBot(
    token=config["data"]["token"],
    # help_class=None,
    intents=hikari.Intents.ALL_UNPRIVILEGED
    | hikari.Intents.MESSAGE_CONTENT
    | hikari.Intents.GUILD_MEMBERS,
)
lightbulb_client = lightbulb.client_from_app(bot)

@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    await lightbulb_client.start()

if os.path.exists("meta.json"):
    with open("meta.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        WELCOME_CHANNEL: hikari.GuildChannel = data["Welcome channel ID"]
        WELCOME_MESSAGE: str = data["Welcome message"]
        NO_TEXT_CATEGORIES: List[int] = data["No-text categories"]
else:
    raise FileExistsError("meta.json is missing.\n"
                          "If you cloned or pulled the git repo, "
                          "make sure to copy example.meta.json, "
                          "name it meta.json and edit for your needs.")

DIRECTION_CHOICES = choicify(["up", "down", "left", "right"])

@lightbulb_client.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    """Error handler"""
    handled = False
    if exc.pipeline.invocation_failed:
        error_cause = exc.invocation_failure
    else:
        error_cause = exc.hook_failures[0]
    error_message = ""
    if isinstance(error_cause, AssertionError):
        error_message = str(error_cause)
        handled = True
    else:
        traceback = error_cause.__traceback__
        while traceback.tb_next: traceback = traceback.tb_next
        filename = os.path.split(traceback.tb_frame.f_code.co_filename)[1]
        line_number = traceback.tb_lineno
        error_message = f"{error_cause.__class__.__name__} " \
                        f"({filename}, line {line_number}): {error_cause}"
    embed = hikari.Embed(
        title = "Error!",
        description = f"An error occurred while attempting to use `/{exc.context.command_data.name}`.\n"
                      f"Error message: `{error_message}`"
    )
    await exc.context.respond(embed, ephemeral=True)
    return handled

@bot.listen()
async def on_join(event: hikari.MemberCreateEvent) -> None:
    message = WELCOME_MESSAGE.format(mention=event.member.mention)
    channel = WELCOME_CHANNEL
    await bot.rest.create_message(channel, message)

async def delete_if_necessary(message: hikari.Message):
    if not message.content:
        return
    text = message.content
    text = re.sub(r"<[@#]\d+?>", "", text)
    text = re.sub(r"https?://[A-Za-z0-9-]+\.[A-Za-z0-9.-]+(/\S+)?", "", text)
    if re.match(r"\s*$", text):
        return
    channel: hikari.GuildChannel = await message.fetch_channel()
    if channel.type not in [hikari.ChannelType.GUILD_TEXT, hikari.ChannelType.GUILD_VOICE]:
        return
    category_id = channel.parent_id
    if category_id in NO_TEXT_CATEGORIES:
        await message.delete()

@bot.listen()
async def on_message_create(event: hikari.MessageCreateEvent) -> None:
    if event.is_bot:
        return
    message = event.message
    await delete_if_necessary(message)

@bot.listen()
async def on_message_edit(event: hikari.MessageUpdateEvent) -> None:
    if event.is_bot:
        return
    message = event.message
    await delete_if_necessary(message)

@lightbulb_client.register
class From_code(
    lightbulb.SlashCommand,
    name = "from-code",
    description = "Clear the banner design and create a design by the design code "
                  "(use /getbannercode on the server)",
):
    code = lightbulb.string(
        "code", "Banner design code. Use /getbannercode on the MC server"
    )

    @lightbulb.invoke
    async def from_code(self, ctx: lightbulb.Context) -> None:
        banner_code = self.code
        banner = banner_designs[ctx.user.id] = Banner.from_banner_code(banner_code)
        save_banner_data()
        await respond_with_banner(ctx, banner)


@lightbulb_client.register
class from_text(
    lightbulb.SlashCommand,
    name="from-text",
    description="Clear the banner design and create a design using the text.",
):
    text = lightbulb.string(
        "text", "Banner text. Ideally use the banner font for the best experience"
    )

    @lightbulb.invoke
    async def from_text(self, ctx: lightbulb.Context) -> None:
        banner_text = self.text
        banner = banner_designs[ctx.user.id] = Banner.from_text(banner_text)
        save_banner_data()
        await respond_with_banner(ctx, banner)


@lightbulb_client.register
class from_url(
    lightbulb.SlashCommand,
    name="from-url",
    description="Clear the banner design and create a design using the given URL.",
):
    url = lightbulb.string(
        "url",
        "Banner URL. You can use either planetminecraft.com/banner or banner-writer.web.app",
    )

    @lightbulb.invoke
    async def from_url(self, ctx: lightbulb.Context) -> None:
        banner_url = self.url
        banner = banner_designs[ctx.user.id] = Banner.from_banner_url(banner_url)
        save_banner_data()
        await respond_with_banner(ctx, banner)


@lightbulb_client.register
class save(
    lightbulb.SlashCommand,
    name="save",
    description="Save the current banner design into a set",
):
    name = lightbulb.string("name", "The name of the banner")
    set = lightbulb.string(
        "set", "The name of the set. Last used by default", default=None
    )

    @lightbulb.invoke
    async def save(self, ctx: lightbulb.Context) -> None:
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set)
        assert ctx.user.id in banner_designs, "You must have a banner design"
        banner_set.banners[self.name] = banner_designs[ctx.user.id].copy()
        save_banner_data()
        await ctx.respond(
            f"Saved banner as `{self.name}` to set `{banner_set_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class set_create(
    lightbulb.SlashCommand,
    name="set-create",
    description="Create a new banner set",
):
    name = lightbulb.string(
        "name",
        "The name of the set. Any symbols except space, comma, period, slash, pipe, and underscore",
    )
    writing_direction = lightbulb.string(
        "writing_direction",
        "The standard writing direction. Default is to the right",
        default="right",
        choices=DIRECTION_CHOICES,
    )
    newline_direction = lightbulb.string(
        "newline_direction",
        "The direction of a newline. Default is downwards",
        default="down",
        choices=DIRECTION_CHOICES,
    )
    space_char = lightbulb.string(
        "space_char", "The space character. Default is hyphen", default="-"
    )
    newline_char = lightbulb.string(
        "newline_char", "The newline character. Default is slash", default="/"
    )
    split_mode = lightbulb.string(
        "split_mode",
        "The split mode",
        default=SplitMode.No.value,
        choices=[lightbulb.Choice(s.value, s.value) for s in SplitMode],
    )

    @lightbulb.invoke
    async def set_create(self, ctx: lightbulb.Context) -> None:
        assert not (
            set(self.name) & set(" ,./|_")
        ), f"Invalid set name: {self.name}"
        assert self.name not in banner_sets.get(
            ctx.user.id, {}
        ), f"You already have a set named {self.name}"
        assert (
            len(self.space_char) == 1
        ), f"Space character must be one character, not {len(self.space_char)}"
        assert (
            len(self.newline_char) == 1
        ), f"Newline character must be one character, not {len(self.newline_char)}"
        assert (
            self.space_char != self.newline_char
        ), "Space character and newline character must be distinct"
        writing_direction = getattr(Direction, self.writing_direction.title())
        newline_direction = getattr(Direction, self.newline_direction.title())
        assert (
            writing_direction.value % 2 != newline_direction.value % 2
        ), "Writing direction and newline direction must be perpendicular"
        split_mode = [s for s in SplitMode if s.value == self.split_mode][0]
        banner_set = BannerSet(
            writing_direction,
            newline_direction,
            self.space_char,
            self.newline_char,
            split_mode,
        )
        banner_sets.setdefault(ctx.user.id, {})
        banner_sets[ctx.user.id][self.name] = banner_set
        last_used[ctx.user.id] = self.name
        save_banner_data()
        await ctx.respond(
            f"Created banner set `{self.name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class say(
    lightbulb.SlashCommand,
    name="say",
    description="Compile a message into banners from a set.",
):
    message = lightbulb.string("message", "Your message")
    set = lightbulb.string(
        "set", "The name of the banner set to use. Default is last used", default=None
    )
    scale = lightbulb.integer(
        "scale",
        "The value to scale by. Default is 2x texture size",
        default=2,
    )
    margin = lightbulb.integer(
        "margin",
        "The margin of pixels. Default is 4x the scale",
        default=None,
    )
    spacing = lightbulb.integer(
        "spacing",
        "The space between any two banners in pixels. Default is 4x the scale",
        default=None,
    )

    @lightbulb.invoke
    async def say(self, ctx: lightbulb.Context) -> None:
        scale = self.scale
        assert scale > 0, "Scale must be positive"
        margin = self.margin or 4 * scale
        assert margin >= 0, "Margin must be nonnegative"
        spacing = self.spacing or 4 * scale
        assert spacing >= 0, "Spacing must be nonnegative"
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set)
        lines = self.message.split(banner_set.newline_char)
        words: list[list[str]] = [line.split(banner_set.space_char) for line in lines]
            # if word == banner_set.space_char:
            #     banners[-1].append(None)
            # elif word == banner_set.newline_char:
            #     banners.append([])
            # else:
            #     assert (
            #         word in banner_set.banners
            #     ), f"Banner set {banner_set_name} does not have a banner for {word}"
            #     banners[-1].append(banner_set.banners[word])
        split_mode = banner_set.split_mode
        split_func = split_mode.split
        names = list(banner_set.banners.keys())
        banners: list[list[Banner]] = []
        for line in words:
            banners.append([])
            for i, word in enumerate(line):
                if i > 0: banners[-1].append(None)
                subwords = word.split()
                for subword in subwords:
                    split = split_func(subword, names)
                    assert split is not None, \
                        (f"Banner set {banner_set_name} doesn’t have a banner for “{word}”"
                        if split_mode == SplitMode.No else
                        f"Could not split “{word}” into {banner_set_name} banners")
                    banners[-1] += [banner_set.banners[b] for b in split]
        output = [
            [
                (
                    banner.image.resize(
                        (20 * scale, 40 * scale), Image.Resampling.NEAREST
                    )
                    if banner
                    else None
                )
                for banner in line
            ]
            for line in banners
        ]
        row_length = max(map(len, output))
        output = [row + [None] * (row_length - len(row)) for row in output]
        image_rows, image_cols = len(output), len(output[0])
        if banner_set.writing_direction.value % 2 == 0:
            image_rows, image_cols = image_cols, image_rows
        image_width = image_cols * 20 * scale + margin * 2 + spacing * (image_cols - 1)
        image_height = image_rows * 40 * scale + margin * 2 + spacing * (image_rows - 1)
        image = Image.new("RGBA", (image_width, image_height))
        for r, row in enumerate(output):
            if banner_set.newline_direction == Direction.Up:
                paste_row = image_rows - r - 1
            elif banner_set.newline_direction == Direction.Down:
                paste_row = r
            elif banner_set.newline_direction == Direction.Left:
                paste_col = image_cols - r - 1
            elif banner_set.newline_direction == Direction.Right:
                paste_col = r
            for c, sprite in enumerate(row):
                if not sprite:
                    continue
                if banner_set.writing_direction == Direction.Up:
                    paste_row = image_rows - c - 1
                elif banner_set.writing_direction == Direction.Down:
                    paste_row = c
                elif banner_set.writing_direction == Direction.Left:
                    paste_col = image_cols - c - 1
                elif banner_set.writing_direction == Direction.Right:
                    paste_col = c
                paste_x = paste_col * 20 * scale + margin + spacing * paste_col
                paste_y = paste_row * 40 * scale + margin + spacing * paste_row
                image.paste(sprite, (paste_x, paste_y))

        async def say_callback(img):
            await ctx.respond(
                writing_description(
                    banners, banner_set.writing_direction, banner_set.newline_direction
                ),
                attachment=hikari.File(img),
                ephemeral = True,
            )

        await save_temporarily(say_callback, image)


@lightbulb_client.register
class set_edit(
    lightbulb.SlashCommand,
    name="set-edit",
    description="Edit the settings of a banner set. Default for all options is no change",
):
    set = lightbulb.string(
        "set", "The name of the banner set to use. Default is last used", default=None
    )
    name = lightbulb.string(
        "name",
        "The new name of the set. Any symbols except space, comma, period, slash, pipe, and underscore",
        default=None,
    )
    writing_direction = lightbulb.string(
        "writing_direction",
        "The standard writing direction",
        default=None,
        choices=DIRECTION_CHOICES,
    )
    newline_direction = lightbulb.string(
        "newline_direction",
        "The direction of a newline",
        default=None,
        choices=DIRECTION_CHOICES,
    )
    space_char = lightbulb.string("space_char", "The space character", default=None)
    newline_char = lightbulb.string(
        "newline_char", "The newline character", default=None
    )
    split_mode = lightbulb.string(
        "split_mode",
        "The split mode",
        default=None,
        choices=[lightbulb.Choice(s.value, s.value) for s in SplitMode],
    )

    @lightbulb.invoke
    async def set_edit(self, ctx: lightbulb.Context) -> None:
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set, update_last_used=False)
        new_name = self.name or banner_set_name
        banner_sets.setdefault(ctx.user.id, {})
        writing_direction = (
            getattr(Direction, self.writing_direction.title())
            if self.writing_direction
            else banner_set.writing_direction
        )
        newline_direction = (
            getattr(Direction, self.newline_direction.title())
            if self.newline_direction
            else banner_set.newline_direction
        )
        space_char = self.space_char or banner_set.space_char
        newline_char = self.newline_char or banner_set.newline_char
        split_mode = (
            [s for s in SplitMode if s.value == self.split_mode][0]
            if self.split_mode
            else banner_set.split_mode
        )
        assert (
            banner_set_name in banner_sets[ctx.user.id]
        ), f"Banner set {banner_set_name} does not exist"
        assert (
            new_name == banner_set_name or new_name not in banner_sets[ctx.user.id]
        ), f"Banner set {new_name} already exists"
        assert not (set(new_name) & set(" ,./|_")), f"Invalid set name: {new_name}"
        assert (
            len(space_char) == 1
        ), f"Space character must be one character, not {len(space_char)}"
        assert (
            len(newline_char) == 1
        ), f"Newline character must be one character, not {len(newline_char)}"
        assert (
            space_char != newline_char
        ), "Space character and newline character must be distinct"
        assert (
            writing_direction.value % 2 != newline_direction.value % 2
        ), "Writing direction and newline direction must be perpendicular"
        last_used[ctx.user.id] = new_name
        new_banner_set = BannerSet(
            writing_direction, newline_direction, space_char, newline_char, split_mode
        )
        new_banner_set.banners = banner_set.banners
        banner_sets[ctx.user.id].pop(banner_set_name)
        banner_sets[ctx.user.id][new_name] = new_banner_set
        save_banner_data()
        await ctx.respond(
            f"Edited banner set `{new_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class set_delete(
    lightbulb.SlashCommand,
    name="set-delete",
    description="Delete a banner set",
):
    set = lightbulb.string(
        "set", "The name of the banner set to use. Default is last used", default=None
    )

    @lightbulb.invoke
    async def set_delete(self, ctx: lightbulb.Context) -> None:
        _, banner_set_name = get_working_set(ctx.user.id, self.set, update_last_used=False)
        if last_used[ctx.user.id] == banner_set_name:
            last_used.pop(ctx.user.id, None)
        banner_sets[ctx.user.id].pop(banner_set_name, None)
        save_banner_data()
        await ctx.respond(
            f"Deleted banner set `{banner_set_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class delete(
    lightbulb.SlashCommand,
    name="delete",
    description="Delete a banner",
):
    name = lightbulb.string("name", "The name of the banner")
    set = lightbulb.string(
        "set", "The name of the set. Last used by default", default=None
    )

    @lightbulb.invoke
    async def delete(self, ctx: lightbulb.Context) -> None:
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set)
        assert (
            self.name in banner_set.banners
        ), f"Banner {self.name} does not exist"
        banner_set.banners.pop(self.name)
        save_banner_data()
        await ctx.respond(
            f"Deleted banner `{self.name}` from set `{banner_set_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class rename(
    lightbulb.SlashCommand,
    name="rename",
    description="Rename a banner",
):
    name = lightbulb.string("name", "The name of the banner")
    new_name = lightbulb.string("new_name", "The new name of the banner")
    set = lightbulb.string(
        "set", "The name of the set. Last used by default", default=None
    )

    @lightbulb.invoke
    async def rename(self, ctx: lightbulb.Context) -> None:
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set)
        assert (
            self.name in banner_set.banners
        ), f"Banner {self.name} does not exist"
        assert (
            self.new_name not in banner_set.banners
        ), f"Banner {self.new_name} already exists"
        banner_set.banners[self.new_name] = banner_set.banners.pop(
            self.name
        )
        save_banner_data()
        await ctx.respond(
            f"Renamed banner `{self.name}` to `{self.new_name}` from set `{banner_set_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class set_rename(
    lightbulb.SlashCommand,
    name="set-rename",
    description="Rename a set",
):
    name = lightbulb.string("name", "The name of the set")
    new_name = lightbulb.string("new_name", "The new name of the set")

    @lightbulb.invoke
    async def set_rename(self, ctx: lightbulb.Context) -> None:
        banner_sets.setdefault(ctx.user.id, {})
        assert (
            self.name in banner_sets[ctx.user.id]
        ), f"Banner set {self.name} does not exist"
        assert (
            self.new_name not in banner_sets[ctx.user.id]
        ), f"Banner set {self.new_name} already exists"
        banner_sets[ctx.user.id][self.new_name] = banner_sets[
            ctx.user.id
        ].pop(self.name)
        last_used[ctx.user.id] = self.new_name
        save_banner_data()
        await ctx.respond(
            f"Renamed banner set `{self.name}` to `{self.new_name}`!",
            ephemeral = True,
        )


@lightbulb_client.register
class set_list(
    lightbulb.SlashCommand,
    name="set-list",
    description="List all your banner sets",
):
    @lightbulb.invoke
    async def set_list(self, ctx: lightbulb.Context) -> None:
        banner_set_data = banner_sets.get(ctx.user.id, {})
        if not banner_set_data:
            await ctx.respond(
                "You have no banner sets!", ephemeral = True
            )
        else:
            await ctx.respond(
                "Your banner sets:\n- "
                + "\n- ".join(
                    f"{name} ({len(banner_set.banners)} banner{'s' if len(banner_set.banners) != 1 else ''})"
                    for name, banner_set in banner_set_data.items()
                ),
                ephemeral = True,
            )


@lightbulb_client.register
class set_info(
    lightbulb.SlashCommand,
    name="set-info",
    description="List information on a banner set",
):
    set = lightbulb.string(
        "set", "The name of the set. Last used by default", default=None
    )

    @lightbulb.invoke
    async def set_info(self, ctx: lightbulb.Context) -> None:
        banner_set, banner_set_name = get_working_set(ctx.user.id, self.set)
        banners = banner_set.banners
        num_banners_text = "0 banners"
        image = None
        if banners:
            num_banners_text = (
                f"{len(banners)} banner{'s' if len(banners) != 1 else ''}"
            )
            dummy_image = Image.new("RGBA", (1, 1))
            dummy_draw = ImageDraw.Draw(dummy_image)
            max_text_length = int(
                max(dummy_draw.textlength(name, BASE_FONT) for name in banners.keys())
            )
            columns = number_of_columns_for(len(banners))
            image = Image.new(
                "RGBA",
                (
                    10 + (max_text_length + 40) * columns,
                    60 * ((len(banners) + columns - 1) // columns),
                ),
            )
            draw = ImageDraw.Draw(image)
            for i, (name, banner) in enumerate(
                sorted(list(banners.items()), key=lambda x: x[0].lower())
            ):
                x = 10 + (max_text_length + 40) * (i % columns)
                y = 10 + 60 * (i // columns)
                image.paste(banner.image, (x, y))
                draw.text((x + 30, y + 20), name, "#ffffff", BASE_FONT, anchor="lm")

        async def list_callback(img):
            await ctx.respond(
                f"""
# Banner set: {banner_set_name}
Writing direction: {banner_set.writing_direction.name.title()}
Newline direction: {banner_set.newline_direction.name.title()}
Space character: `{banner_set.space_char}`
Newline character: `{banner_set.newline_char}`
Split mode: `{banner_set.split_mode.value}`
## {num_banners_text}
""".strip(),
                attachment=hikari.File(img) if img is not None else None,
                ephemeral = True,
            )

        await save_temporarily(list_callback, image)


@lightbulb_client.register
class load(
    lightbulb.SlashCommand,
    name="load",
    description="Load a banner from a set to replace the current design",
):
    name = lightbulb.string("name", "The name of the banner to load")
    set = lightbulb.string(
        "set", "The name of the set. Last used by default", default=None
    )

    @lightbulb.invoke
    async def load(self, ctx: lightbulb.Context) -> None:
        banner_set, _ = get_working_set(ctx.user.id, self.set)
        banner = banner_set.banners.get(self.name)
        assert banner, f"Banner {self.name} does not exist"
        banner_designs[ctx.user.id] = banner.copy()
        save_banner_data()
        await respond_with_banner(ctx, banner)


@lightbulb_client.register
class show(
    lightbulb.SlashCommand,
    name="show",
    description="Show the current banner design",
):
    @lightbulb.invoke
    async def show(self, ctx: lightbulb.Context) -> None:
        if ctx.user.id not in banner_designs:
            await ctx.respond(
                "You don't have a banner design at the moment!",
                ephemeral = True,
            )
        else:
            await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class add(
    lightbulb.SlashCommand,
    name="add",
    description="Add a pattern to the banner design",
):
    pattern = lightbulb.string(
        "pattern", "The banner pattern to add", autocomplete=pattern_autocomplete
    )
    color = lightbulb.string(
        "color", "The color of the pattern to add", choices=COLOR_CHOICES
    )
    layer = lightbulb.string(
        "layer",
        "The layer to insert before. Defaults to adding to the end",
        autocomplete=layer_autocomplete,
        default=None,
    )

    @lightbulb.invoke
    async def add(self, ctx: lightbulb.Context) -> None:
        if ctx.user.id not in banner_designs:
            await ctx.respond(
                "You don't have a banner design at the moment!",
                ephemeral = True,
            )
        else:
            index = None
            if self.layer is not None:
                index = layer_to_index(ctx, self.layer)
            for pattern in Pattern:
                if pattern.pretty_name == self.pattern:
                    break
            else:
                raise ValueError(f"Invalid pattern: {self.pattern}")
            for color in Color:
                if color.pretty_name == self.color:
                    break
            else:
                raise ValueError("Impossible")
            new_layer = Layer(color, pattern)
            layers = banner_designs[ctx.user.id].layers
            if index is None:
                layers.append(new_layer)
            else:
                assert (
                    1 <= index <= len(layers)
                ), f"Cannot insert before layer {self.layer}"
                layers.insert(index - 1, new_layer)
            save_banner_data()
            await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class remove(
    lightbulb.SlashCommand,
    name="remove",
    description="Remove a pattern from the banner design",
):
    layer = lightbulb.string(
        "layer",
        "The layer to remove. Defaults to removing the last layer",
        autocomplete=layer_autocomplete,
        default=None,
    )

    @lightbulb.invoke
    async def remove(self, ctx: lightbulb.Context) -> None:
        if ctx.user.id not in banner_designs:
            await ctx.respond(
                "You don't have a banner design at the moment!",
                ephemeral = True,
            )
        else:
            index = layer_to_index(ctx, self.layer)
            layers = banner_designs[ctx.user.id].layers
            if index is None:
                layers.pop()
            else:
                assert (
                    1 <= index <= len(layers)
                ), f"Cannot remove layer {self.layer}"
                layers.pop(index - 1)
            save_banner_data()
            await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class new(
    lightbulb.SlashCommand,
    name="new",
    description="Clear the banner design and create a new one",
):
    base_color = lightbulb.string(
        "base_color",
        "The base color of the new banner. Defaults to white",
        choices=COLOR_CHOICES,
        default="White",
    )

    @lightbulb.invoke
    async def new(self, ctx: lightbulb.Context) -> None:
        for color in Color:
            if color.pretty_name == self.base_color:
                break
        else:
            raise ValueError("Impossible")
        banner_designs[ctx.user.id] = Banner(color, [])
        save_banner_data()
        await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class edit(
    lightbulb.SlashCommand,
    name="edit",
    description="Edit the banner base or a banner layer",
):
    edit_layer = lightbulb.string(
        "edit_layer",
        "The layer to edit. Defaults to the banner base",
        autocomplete=layer_autocomplete,
        default=None,
    )
    pattern = lightbulb.string(
        "pattern", "Pattern name", autocomplete=pattern_autocomplete, default=None
    )
    color = lightbulb.string(
        "color", "Color of the pattern", choices=COLOR_CHOICES, default=None
    )

    @lightbulb.invoke
    async def edit(self, ctx: lightbulb.Context) -> None:
        if ctx.user.id not in banner_designs:
            await ctx.respond(
                "You don't have a banner design at the moment!",
                ephemeral = True,
            )
        else:
            index = layer_to_index(ctx, self.edit_layer)
            layers = banner_designs[ctx.user.id].all_layers
            if index is None:
                assert (
                    not self.pattern
                ), "Cannot set the pattern of the base layer"
                index = 0
            else:
                assert 1 <= index < len(layers), f"Cannot edit layer {index}"
            if self.color:
                for color in Color:
                    if color.pretty_name == self.color:
                        break
                else:
                    raise ValueError("Impossible")
            else:
                color = layers[index].color
            if self.pattern:
                for pattern in Pattern:
                    if pattern.pretty_name == self.pattern:
                        break
                else:
                    raise ValueError(f"Invalid pattern: {self.pattern}")
            else:
                pattern = layers[index].pattern
            layers[index].set(Layer(color, pattern))
            banner_designs[ctx.user.id] = Banner(layers[0].color, layers[1:])
            save_banner_data()
            await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class poop(
    lightbulb.SlashCommand,
    name="poop",
    description="poop banner",
):
    for_everyone = lightbulb.boolean(
        "for_everyone", "Set to true to send to everyone", default=False
    )

    @lightbulb.invoke
    async def poop(self, ctx: lightbulb.Context) -> None:
        await respond_with_banner(
            ctx,
            Banner(
                Color.Brown,
                [
                    Layer(Color.Pink, x)
                    for x in [
                        Pattern.BordureIndented,
                        Pattern.PerBend,
                        Pattern.PerBendSinister,
                    ]
                ],
            ),
            self.for_everyone,
        )


@lightbulb_client.register
class clear(
    lightbulb.SlashCommand,
    name="clear",
    description="Clears the banner design",
):
    @lightbulb.invoke
    async def clear(self, ctx: lightbulb.Context) -> None:
        if ctx.user.id not in banner_designs:
            await ctx.respond(
                "You don't have a banner design at the moment!",
                ephemeral = True,
            )
        else:
            banner_designs[ctx.user.id].layers = []
            save_banner_data()
            await respond_with_banner(ctx, banner_designs[ctx.user.id])


@lightbulb_client.register
class patterns(
    lightbulb.SlashCommand,
    name="patterns",
    description="List all banner patterns",
):
    @lightbulb.invoke
    async def patterns(self, ctx: lightbulb.Context) -> None:
        output = []
        output_images = {}
        for pattern in Pattern:
            if pattern == Pattern.Banner:
                banner = Banner(Color.Black, [])
            else:
                banner = Banner(Color.White, [Layer(Color.Black, pattern)])
            output.append(pattern.pretty_name + " " + banner.text)
            output_images[pattern.pretty_name_no_char] = banner.image
        columns = number_of_columns_for(len(output_images))
        dummy_image = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_image)
        max_text_length = int(
            max(dummy_draw.textlength(name, BASE_FONT) for name in output_images.keys())
        )
        image = Image.new(
            "RGBA",
            (
                10 + (max_text_length + 40) * columns,
                60 * ((len(output_images) + columns - 1) // columns),
            ),
        )
        draw = ImageDraw.Draw(image)
        for i, (name, banner) in enumerate(
            sorted(list(output_images.items()), key=lambda x: x[0].lower())
        ):
            x = 10 + (max_text_length + 40) * (i % columns)
            y = 10 + 60 * (i // columns)
            image.paste(banner, (x, y))
            draw.text((x + 30, y + 20), name, "#ffffff", BASE_FONT, anchor="lm")

        async def callback(img):
            await ctx.respond(
                "\n".join(output),
                ephemeral = True,
                attachment=hikari.File(img),
            )

        await save_temporarily(callback, image)


# Temporarily removed the /help command until I figure out how the hell it’s supposed to work

# @lightbulb_client.register
# class help_command(
#     lightbulb.SlashCommand,
#     name="help",
#     description="Provides help on commands",
# ):
#     command = lightbulb.string(
#         "command",
#         "Command to get help on",
#         default=None,
#         choices=list(bot.slash_commands.keys()) + ["help"],
#     )

#     @lightbulb.invoke
#     async def help_command(self, ctx: lightbulb.Context) -> None:
#         help_data = {}
#         for k, v in bot.slash_commands.items():
#             required_args = ""
#             optional_args = ""
#             for option in v.options.values():
#                 inner_part = option.name
#                 if option.arg_type != str:
#                     inner_part += f": {option.arg_type.__name__}"
#                 if option.required:
#                     required_args += f" <{inner_part}>"
#                 else:
#                     optional_args += f" [{inner_part}]"
#             usage = "/" + v.name + required_args + optional_args
#             help_data[k] = {
#                 "text": v.description,
#                 "usage": usage,
#                 "params": [
#                     f"`{option.name}`: {urlize(option.description)}"
#                     for option in v.options.values()
#                 ],
#             }
#         if not self.command:
#             output = "# Command list:\n- " + "\n- ".join(
#                 f"`{x['usage']}` {x['text']}" for x in help_data.values()
#             )
#         else:
#             output = f"`{help_data[self.command]['usage']}`\n{help_data[self.command]['text']}"
#             for param in help_data[self.command]["params"]:
#                 output += f"\n- {param}"
#         await ctx.respond(output, ephemeral = True)


bot.run()
