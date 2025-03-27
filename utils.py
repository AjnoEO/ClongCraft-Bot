import lightbulb
import os
from pathlib import Path
import random
import re
from PIL import Image, ImageFont

class JSONifyable:
    @property
    def args(self): ...
	
    def jsonify(self): return {"__type": self.__class__.__name__, "args": self.args}

class UserError(Exception): ...

BASE_FONT = ImageFont.truetype(font="font_noto/NotoSans.ttf")

def urlize(string):
	return re.sub(r"((https?://)?([\w\d-]+(\.[\w\d-]+)*(\.[\w\d-]{1,4})(/[^/\s]+)*)/?)", r"[\1](<https://\3>)", string)

def choicify(choices: list[str]):
	return [lightbulb.Choice(c, c) for c in choices]

async def save_temporarily(callback, image: Image.Image | None, *args):
	if image is None:
		await callback(None, *args)
		return None
	temp_path = "temp"
	Path(temp_path).mkdir(parents=True, exist_ok=True)
	while True:
		filename = "".join(chr(random.randint(ord("a"), ord("z"))) for _ in range(8))
		path = os.path.join(temp_path, filename + ".png")
		if path not in os.listdir(temp_path): break
	image.save(path)
	await callback(path, *args)
	os.remove(path)
