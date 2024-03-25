import hikari, lightbulb, os, json
from json import JSONDecoder
from configparser import ConfigParser
from banner import *
from utils import *
from typing import Dict, List, Optional
from PIL import Image, ImageDraw
import re

# https://discord.com/api/oauth2/authorize?client_id=1175889917990154250&permissions=2147494976&scope=bot

config = ConfigParser()
config.read("config.ini")

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

async def layer_autocomplete(option, interaction) -> List[str]:
	banner = banner_designs.get(interaction.user.id)
	if not banner: return []
	layers = [f"{i+1}. {layer.color.pretty_name} {layer.pattern.pretty_name}" for i, layer in enumerate(banner.layers)]
	input_data = option.value.lower()
	return [layer for layer in layers if input_data in layer.lower()]

def layer_to_index(ctx, layer) -> Optional[int]:
	banner = banner_designs.get(ctx.author.id)
	if not banner: return
	layers = [f"{i+1}. {this_layer.color.pretty_name} {this_layer.pattern.pretty_name}"
			  for i, this_layer in enumerate(banner.layers)]
	for i, possible_layer in enumerate(layers):
		if layer.lower() in possible_layer.lower(): return i + 1

bot = lightbulb.BotApp(token = config["data"]["token"], help_class = None)

@bot.listen(lightbulb.CommandErrorEvent)
async def on_error(event: lightbulb.CommandErrorEvent) -> None:
	if isinstance(event.exception, lightbulb.CommandInvocationError):
		embed = hikari.embeds.Embed(
			title = "Error!",
			description = f"An error occurred while attempting to use `/{event.context.command.name}`.\n"
						  f"Error message: `{event.exception.__cause__}`"
		)
		await event.context.respond(embed, flags = hikari.messages.MessageFlag.EPHEMERAL)
		return
	# Unwrap the exception to get the original cause
	exception = event.exception.__cause__ or event.exception
	if isinstance(exception, lightbulb.NotOwner):
		await event.context.respond("You are not the owner of this bot.", flags = hikari.messages.MessageFlag.EPHEMERAL)
	elif isinstance(exception, lightbulb.CommandIsOnCooldown):
		await event.context.respond(f"This command is on cooldown. Retry in `{exception.retry_after:.2f}` seconds.",
									flags = hikari.messages.MessageFlag.EPHEMERAL)
	else:
		await event.context.respond(r"Uncaught exception! Check the console, <@708440911591243826>. *\*dies\**")
		raise exception

@bot.command
@lightbulb.option("code", "Banner design code. Use /getbannercode on the MC server")
@lightbulb.command("from-code", "Clear the banner design and create a design by the design code "
								"(use /getbannercode on the server)")
@lightbulb.implements(lightbulb.SlashCommand)
async def from_code(ctx: lightbulb.Context) -> None:
	banner_code = ctx.options.code
	banner = banner_designs[ctx.author.id] = Banner.from_banner_code(banner_code)
	save_banner_data()
	await respond_with_banner(ctx, banner)

@bot.command
@lightbulb.option("text", "Banner text. Ideally use the banner font for the best experience")
@lightbulb.command("from-text", "Clear the banner design and create a design using the text.")
@lightbulb.implements(lightbulb.SlashCommand)
async def from_text(ctx: lightbulb.Context) -> None:
	banner_text = ctx.options.text
	banner = banner_designs[ctx.author.id] = Banner.from_text(banner_text)
	save_banner_data()
	await respond_with_banner(ctx, banner)

@bot.command
@lightbulb.option("url", "Banner URL. Use the website https://www.planetminecraft.com/banner/")
@lightbulb.command("from-url", "Clear the banner design and create a design using the given URL.")
@lightbulb.implements(lightbulb.SlashCommand)
async def from_url(ctx: lightbulb.Context) -> None:
	banner_url = ctx.options.url
	banner = banner_designs[ctx.author.id] = Banner.from_banner_url(banner_url)
	save_banner_data()
	await respond_with_banner(ctx, banner)

@bot.command
@lightbulb.option("name", "The name of the banner")
@lightbulb.option("set", "The name of the set. Last used by default", default = None)
@lightbulb.command("save", "Save the current banner design into a set")
@lightbulb.implements(lightbulb.SlashCommand)
async def save(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	assert ctx.author.id in banner_designs, "You must have a banner design"
	last_used[ctx.author.id] = banner_set_name
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	banner_set.banners[ctx.options.name] = banner_designs[ctx.author.id]
	save_banner_data()
	await ctx.respond(
		f"Saved banner as `{ctx.options.name}` to set `{banner_set_name}`!",
		flags = hikari.messages.MessageFlag.EPHEMERAL
	)

@bot.command
@lightbulb.option("name", "The name of the set. Any symbols except space, comma, period, slash, pipe, and underscore")
@lightbulb.option("writing_direction", "The standard writing direction. Default is to the right",
				  default = "right", choices = ["up", "down", "left", "right"])
@lightbulb.option("newline_direction", "The direction of a newline. Default is downwards",
				  default = "down", choices = ["up", "down", "left", "right"])
@lightbulb.option("space_char", "The space character. Default is hyphen", default = "-")
@lightbulb.option("newline_char", "The newline character. Default is slash", default = "/")
@lightbulb.command("set-create", "Create a new banner set")
@lightbulb.implements(lightbulb.SlashCommand)
async def set_create(ctx: lightbulb.Context) -> None:
	assert not (set(ctx.options.name) & set(" ,./|_")), f"Invalid set name: {ctx.options.name}"
	assert len(ctx.options.space_char) == 1, f"Space character must be one character, not {len(ctx.options.space_char)}"
	assert len(ctx.options.newline_char) == 1, \
		f"Newline character must be one character, not {len(ctx.options.newline_char)}"
	assert ctx.options.space_char != ctx.options.newline_char, "Space character and newline character must be distinct"
	writing_direction = getattr(Direction, ctx.options.writing_direction.title())
	newline_direction = getattr(Direction, ctx.options.newline_direction.title())
	assert writing_direction.value % 2 != newline_direction.value % 2, \
		"Writing direction and newline direction must be perpendicular"
	banner_set = BannerSet(writing_direction, newline_direction, ctx.options.space_char, ctx.options.newline_char)
	banner_sets.setdefault(ctx.author.id, {})
	banner_sets[ctx.author.id][ctx.options.name] = banner_set
	last_used[ctx.author.id] = ctx.options.name
	save_banner_data()
	await ctx.respond(
		f"Created banner set `{ctx.options.name}`!",
		flags = hikari.messages.MessageFlag.EPHEMERAL
	)

@bot.command
@lightbulb.option("message", "Your message")
@lightbulb.option("set", "The name of the banner set to use. Default is last used", default = None)
@lightbulb.option("scale", "The value to scale by. Default is 2x texture size", default = 2, type = int)
@lightbulb.option("margin", "The margin of pixels. Default is 4x the scale", default = None, type = int)
@lightbulb.option("spacing", "The space between any two banners in pixels. Default is 4x the scale", default = None,
				  type = int)
@lightbulb.command("say", "Compile a message into banners from a set.")
@lightbulb.implements(lightbulb.SlashCommand)
async def say(ctx: lightbulb.Context) -> None:
	scale = ctx.options.scale
	assert scale > 0, "Scale must be positive"
	margin = ctx.options.margin or 4 * scale
	assert margin >= 0, "Margin must be nonnegative"
	spacing = ctx.options.spacing or 4 * scale
	assert spacing >= 0, "Spacing must be nonnegative"
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	last_used[ctx.author.id] = banner_set_name
	assert banner_set_name, "You must have a banner set"
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	words = ctx.options.message.split()
	output = [[]]
	for word in words:
		if word == banner_set.space_char: output[-1].append(None)
		elif word == banner_set.newline_char: output.append([])
		else:
			assert word in banner_set.banners, f"Banner set {banner_set_name} does not have a banner for {word}"
			output[-1].append(banner_set.banners[word].image.resize((20 * scale, 40 * scale), Image.Resampling.NEAREST))
	row_length = max(map(len, output))
	output = [row + [None] * (row_length - len(row)) for row in output]
	image_rows, image_cols = len(output), len(output[0])
	if banner_set.writing_direction.value % 2 == 0: image_rows, image_cols = image_cols, image_rows
	image_width = image_cols * 20 * scale + margin * 2 + spacing * (image_cols - 1)
	image_height = image_rows * 40 * scale + margin * 2 + spacing * (image_rows - 1)
	image = Image.new("RGBA", (image_width, image_height))
	for r, row in enumerate(output):
		if banner_set.newline_direction == Direction.Up: paste_row = image_rows - r - 1
		elif banner_set.newline_direction == Direction.Down: paste_row = r
		elif banner_set.newline_direction == Direction.Left: paste_col = image_cols - r - 1
		elif banner_set.newline_direction == Direction.Right: paste_col = r
		for c, sprite in enumerate(row):
			if not sprite: continue
			if banner_set.writing_direction == Direction.Up: paste_row = image_rows - c - 1
			elif banner_set.writing_direction == Direction.Down: paste_row = c
			elif banner_set.writing_direction == Direction.Left: paste_col = image_cols - c - 1
			elif banner_set.writing_direction == Direction.Right: paste_col = c
			paste_x = paste_col * 20 * scale + margin + spacing * paste_col
			paste_y = paste_row * 20 * scale + margin + spacing * paste_row
			image.paste(sprite, (paste_x, paste_y))
	async def say_callback(img):
		await ctx.respond(hikari.File(img), flags = hikari.messages.MessageFlag.EPHEMERAL)
	await save_temporarily(say_callback, image)

@bot.command
@lightbulb.option("set", "The name of the banner set to use. Default is last used", default = None)
@lightbulb.option("name",
				  "The new name of the set. Any symbols except space, comma, period, slash, pipe, and underscore",
				  default = None)
@lightbulb.option("writing_direction", "The standard writing direction",
				  default = None, choices = ["up", "down", "left", "right"])
@lightbulb.option("newline_direction", "The direction of a newline",
				  default = None, choices = ["up", "down", "left", "right"])
@lightbulb.option("space_char", "The space character", default = None)
@lightbulb.option("newline_char", "The newline character", default = None)
@lightbulb.command("set-edit", "Edit the settings of a banner set. Default for all options is no change")
@lightbulb.implements(lightbulb.SlashCommand)
async def set_edit(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	last_used[ctx.author.id] = banner_set_name
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	new_name = ctx.options.name or banner_set_name
	writing_direction = (
		getattr(Direction, ctx.options.writing_direction.title())
		if ctx.options.writing_direction else banner_set.writing_direction
	)
	newline_direction = (
		getattr(Direction, ctx.options.newline_direction.title())
		if ctx.options.newline_direction else banner_set.newline_direction
	)
	space_char = ctx.options.space_char or banner_set.space_char
	newline_char = ctx.options.newline_char or banner_set.newline_char
	assert not (set(new_name) & set(" ,./|_")), f"Invalid set name: {new_name}"
	assert len(space_char) == 1, f"Space character must be one character, not {len(space_char)}"
	assert len(newline_char) == 1, f"Newline character must be one character, not {len(newline_char)}"
	assert space_char != newline_char, "Space character and newline character must be distinct"
	assert writing_direction.value % 2 != newline_direction.value % 2, \
		"Writing direction and newline direction must be perpendicular"
	new_banner_set = BannerSet(writing_direction, newline_direction, space_char, newline_char)
	new_banner_set.banners = banner_set.banners
	banner_sets[ctx.author.id].pop(banner_set_name)
	banner_sets[ctx.author.id][new_name] = new_banner_set
	save_banner_data()
	await ctx.respond(
		f"Edited banner set `{new_name}`!",
		flags = hikari.messages.MessageFlag.EPHEMERAL
	)

@bot.command
@lightbulb.option("set", "The name of the banner set to use. Default is last used", default = None)
@lightbulb.command("set-delete", "Delete a banner set")
@lightbulb.implements(lightbulb.SlashCommand)
async def set_delete(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	last_used.pop(ctx.author.id)
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_sets[ctx.author.id].pop(banner_set_name)
	save_banner_data()
	await ctx.respond(
		f"Deleted banner set `{banner_set_name}`!",
		flags = hikari.messages.MessageFlag.EPHEMERAL
	)

@bot.command
@lightbulb.option("name", "The name of the banner")
@lightbulb.option("set", "The name of the set. Last used by default", default = None)
@lightbulb.command("delete", "Delete a banner")
@lightbulb.implements(lightbulb.SlashCommand)
async def delete(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	last_used[ctx.author.id] = banner_set_name
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	assert ctx.options.name in banner_set.banners, f"Banner {ctx.options.name} does not exist"
	banner_set.banners.pop(ctx.options.name)
	save_banner_data()
	await ctx.respond(
		f"Deleted banner `{ctx.options.name}` from set `{banner_set_name}`!",
		flags = hikari.messages.MessageFlag.EPHEMERAL
	)

@bot.command
@lightbulb.command("set-list", "List all your banner sets")
@lightbulb.implements(lightbulb.SlashCommand)
async def set_list(ctx: lightbulb.Context) -> None:
	banner_set_data = banner_sets.get(ctx.author.id, {})
	if not banner_set_data:
		await ctx.respond("You have no banner sets!", flags = hikari.messages.MessageFlag.EPHEMERAL)
	else:
		await ctx.respond(
			"Your banner sets:\n- " + "\n- ".join(
				f"{name} ({len(banner_set.banners)} banner{'s' if len(banner_set.banners) != 1 else ''})"
				for name, banner_set in banner_set_data.items()
			), flags = hikari.messages.MessageFlag.EPHEMERAL
		)

@bot.command
@lightbulb.option("set", "The name of the set. Last used by default", default = None)
@lightbulb.command("set-info", "List information on a banner set")
@lightbulb.implements(lightbulb.SlashCommand)
async def list_banners(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	last_used[ctx.author.id] = banner_set_name
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	banners = banner_set.banners
	num_banners_text = "0 banners"
	image = None
	if banners:
		num_banners_text = \
			f"{len(banners)} banner{'s' if len(banners) != 1 else ''}:\n- " + \
			"\n- ".join(f"{name} {banner.text}" for name, banner in sorted(list(banners.items()),
																		   key = lambda x: x[0].lower()))
		dummy_image = Image.new("RGBA", (1, 1))
		dummy_draw = ImageDraw.Draw(dummy_image)
		max_text_length = int(max(dummy_draw.textlength(name) for name in banners.keys()))
		image = Image.new("RGBA", (50 + max_text_length, 60 * len(banners)))
		draw = ImageDraw.Draw(image)
		for i, (name, banner) in enumerate(sorted(list(banners.items()), key = lambda x: x[0].lower())):
			y = 10 + 60 * i
			image.paste(banner.image, (10, y))
			draw.text((40, y + 10), name, "#ffffff")
	async def list_callback(img):
		await ctx.respond(
			f"""
# Banner set: {banner_set_name}
Writing direction: {banner_set.writing_direction.name.title()}
Newline direction: {banner_set.newline_direction.name.title()}
Space character: `{banner_set.space_char}`
Newline character: `{banner_set.newline_char}`
## {num_banners_text}
""".strip(),
			attachment = hikari.File(img) if img != None else None,
			flags = hikari.messages.MessageFlag.EPHEMERAL
		)
	if image:
		await save_temporarily(list_callback, image)
	else:
		await list_callback(image)

@bot.command
@lightbulb.option("name", "The name of the banner to load")
@lightbulb.option("set", "The name of the set. Last used by default", default = None)
@lightbulb.command("load", "Load a banner from a set to replace the current design")
@lightbulb.implements(lightbulb.SlashCommand)
async def load(ctx: lightbulb.Context) -> None:
	banner_set_name = ctx.options.set or last_used.get(ctx.author.id)
	assert banner_set_name, "You must have a banner set"
	last_used[ctx.author.id] = banner_set_name
	banner_sets.setdefault(ctx.author.id, {})
	assert banner_set_name in banner_sets[ctx.author.id], f"Banner set {banner_set_name} does not exist"
	banner_set = banner_sets[ctx.author.id][banner_set_name]
	banner = banner_set.banners.get(ctx.options.name)
	assert banner, f"Banner {ctx.options.name} does not exist"
	banner_designs[ctx.author.id] = banner.copy()
	save_banner_data()
	await respond_with_banner(ctx, banner)

@bot.command
@lightbulb.command("show", "Show the current banner design")
@lightbulb.implements(lightbulb.SlashCommand)
async def show(ctx: lightbulb.Context) -> None:
	if ctx.author.id not in banner_designs:
		await ctx.respond("You don't have a banner design at the moment!",
						  flags = hikari.messages.MessageFlag.EPHEMERAL)
	else:
		await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.option("pattern", "The banner pattern to add", autocomplete = pattern_autocomplete)
@lightbulb.option("color", "The color of the pattern to add", choices = COLOR_CHOICES)
@lightbulb.option("layer", "The layer to insert before. Defaults to adding to the end",
				  autocomplete = layer_autocomplete, default = None)
@lightbulb.command("add", "Add a pattern to the banner design")
@lightbulb.implements(lightbulb.SlashCommand)
async def add(ctx: lightbulb.Context) -> None:
    if ctx.author.id not in banner_designs:
        await ctx.respond("You don't have a banner design at the moment!",
                          flags = hikari.messages.MessageFlag.EPHEMERAL)
    else:
        index = None
        if ctx.options.layer is not None:
            index = layer_to_index(ctx, ctx.options.layer)
        for pattern in Pattern:
            if pattern.pretty_name == ctx.options.pattern: break
        else: raise ValueError(f"Invalid pattern: {ctx.options.pattern}")
        for color in Color:
            if color.pretty_name == ctx.options.color: break
        else: raise ValueError("Impossible")
        new_layer = Layer(color, pattern)
        layers = banner_designs[ctx.author.id].layers
        if index is None: layers.append(new_layer)
        else:
            assert 1 <= index < len(layers), f"Cannot insert before layer {ctx.options.layer}"
            layers.insert(index-1, new_layer)
        save_banner_data()
        await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.option("layer", "The layer to remove. Defaults to removing the last layer",
				  autocomplete = layer_autocomplete, default = None)
@lightbulb.command("remove", "Remove a pattern from the banner design")
@lightbulb.implements(lightbulb.SlashCommand)
async def remove(ctx: lightbulb.Context) -> None:
	if ctx.author.id not in banner_designs:
		await ctx.respond("You don't have a banner design at the moment!",
						  flags = hikari.messages.MessageFlag.EPHEMERAL)
	else:
		index = layer_to_index(ctx, ctx.options.layer)
		layers = banner_designs[ctx.author.id].layers
		if index is None: layers.pop()
		else:
			assert 1 <= index < len(layers), f"Cannot remove layer {ctx.options.layer}"
			layers.pop(index)
		if not ctx.options.pattern: pattern = layers[index].pattern
		else:
			for pattern in Pattern:
				if pattern.pretty_name == ctx.options.pattern: break
			else: raise ValueError(f"Invalid pattern: {ctx.options.pattern}")
		if not ctx.options.color: color = layers[index].color
		else:
			for color in Color:
				if color.pretty_name == ctx.options.color: break
			else: raise ValueError("Impossible")
		layers[index] = Layer(color, pattern)
		save_banner_data()
		await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.option("base_color", "The base color of the new banner. Defaults to white",
				  choices = COLOR_CHOICES, default = "White")
@lightbulb.command("new", "Clear the banner design and create a new one")
@lightbulb.implements(lightbulb.SlashCommand)
async def new(ctx: lightbulb.Context) -> None:
	for color in Color:
		if color.pretty_name == ctx.options.base_color: break
	else: raise ValueError("Impossible")
	banner_designs[ctx.author.id] = Banner(color, [])
	save_banner_data()
	await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.option("edit_layer", "The layer to edit. Defaults to the banner base",
				  autocomplete = layer_autocomplete, default = None)
@lightbulb.option("pattern", "Pattern name", autocomplete = pattern_autocomplete, default = None)
@lightbulb.option("color", "Color of the pattern", choices = COLOR_CHOICES, default = None)
@lightbulb.command("edit", "Edit the banner base or a banner layer")
@lightbulb.implements(lightbulb.SlashCommand)
async def edit(ctx: lightbulb.Context) -> None:
	if ctx.author.id not in banner_designs:
		await ctx.respond("You don't have a banner design at the moment!",
						  flags=hikari.messages.MessageFlag.EPHEMERAL)
	else:
		index = layer_to_index(ctx, ctx.options.edit_layer)
		layers = banner_designs[ctx.author.id].all_layers
		if index is None:
			assert not ctx.options.pattern, "Cannot set the pattern of the base layer"
			index = 0
		else:
			assert 1 <= index < len(layers), f"Cannot edit layer {index}"
		if ctx.options.color:
			for color in Color:
				if color.pretty_name == ctx.options.color: break
			else: raise ValueError("Impossible")
		else: color = layers[index].color
		if ctx.options.pattern:
			for pattern in Pattern:
				if pattern.pretty_name == ctx.options.pattern: break
			else: raise ValueError(f"Invalid pattern: {ctx.options.pattern}")
		else: pattern = layers[index].pattern
		layers[index].set(Layer(color, pattern))
		save_banner_data()
		await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.option("for_everyone", "Set to true to send to everyone", type = bool, default = False)
@lightbulb.command("poop", "poop banner")
@lightbulb.implements(lightbulb.SlashCommand)
async def poop(ctx: lightbulb.Context) -> None:
	await respond_with_banner(ctx, Banner(Color.Brown, [
		Layer(Color.Pink, x) for x in [Pattern.BordureIndented, Pattern.PerBend, Pattern.PerBendSinister]
	]), ctx.options.for_everyone)

@bot.command
@lightbulb.command("clear", "Clears the banner design")
@lightbulb.implements(lightbulb.SlashCommand)
async def clear(ctx: lightbulb.Context) -> None:
	if ctx.author.id not in banner_designs:
		await ctx.respond("You don't have a banner design at the moment!",
						  flags=hikari.messages.MessageFlag.EPHEMERAL)
	else:
		banner_designs[ctx.author.id].layers = []
		save_banner_data()
		await respond_with_banner(ctx, banner_designs[ctx.author.id])

@bot.command
@lightbulb.command("patterns", "List all banner patterns. Requires banner font")
@lightbulb.implements(lightbulb.SlashCommand)
async def patterns(ctx: lightbulb.Context) -> None:
	output = []
	for pattern in Pattern:
		if pattern == Pattern.Banner:
			output.append(pattern.pretty_name + " " + Banner(Color.Black, []).text)
		else:
			output.append(pattern.pretty_name + " " + Banner(Color.White, [Layer(Color.Black, pattern)]).text)
	await ctx.respond("\n".join(output), flags = hikari.messages.MessageFlag.EPHEMERAL)

@bot.command
@lightbulb.option("command", "Command to get help on", default = None,
				  choices = list(bot.slash_commands.keys()) + ["help"])
@lightbulb.command("help", "Provides help on commands")
@lightbulb.implements(lightbulb.SlashCommand)
async def help_command(ctx: lightbulb.Context) -> None:
	help_data = {}
	for k, v in bot.slash_commands.items():
		required_args = ""
		optional_args = ""
		for option in v.options.values():
			inner_part = option.name
			if option.arg_type != str:
				inner_part += f": {option.arg_type.__name__}"
			if option.required: required_args += f" <{inner_part}>"
			else: optional_args += f" [{inner_part}]"
		usage = "/" + v.name + required_args + optional_args
		help_data[k] = {
			"text": v.description,
			"usage": usage,
			"params": [f"`{option.name}`: {option.description}" for option in v.options.values()]
		}
	if not ctx.options.command:
		output = "# Command list:\n- " + "\n- ".join(f"`{x['usage']}` {x['text']}" for x in help_data.values())
	else:
		output = f"`{help_data[ctx.options.command]['usage']}`\n{help_data[ctx.options.command]['text']}"
		for param in help_data[ctx.options.command]["params"]: output += f"\n- {param}"
	await ctx.respond(output, flags = hikari.messages.MessageFlag.EPHEMERAL)

bot.run()