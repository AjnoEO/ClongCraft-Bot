import hikari
import os
from pathlib import Path
import random
from PIL import Image, ImageFont

BASE_FONT = ImageFont.truetype(font="font_noto/NotoSans.ttf")

async def save_temporarily(callback, image, *args):
	if image == None:
		await callback(None, *args)
		return None
	temp_path = "/temp"
	Path(temp_path).mkdir(parents=True, exist_ok=True)
	while True:
		filename = "".join(chr(random.randint(ord("a"), ord("z"))) for i in range(8))
		path = os.path.join(temp_path, filename + ".png")
		if path not in os.listdir(temp_path): break
	image.save(path)
	await callback(path, *args)
	os.remove(path)

async def pattern_update_callback(path, ctx, text, for_everyone):
	await ctx.respond(
		text,
		attachment = hikari.File(path),
		flags = hikari.messages.MessageFlag.EPHEMERAL if not for_everyone else 0
	)

async def respond_with_banner(ctx, banner, for_everyone = False):
	await save_temporarily(pattern_update_callback, banner.image.resize((80, 160), Image.Resampling.NEAREST),
						   ctx, banner.description, for_everyone)