import lightbulb
import os
from pathlib import Path
import random
import re
from typing import Iterable, TypeVar
from PIL import Image, ImageFont

BASE_FONT = ImageFont.truetype(font="font_noto/NotoSans.ttf")
RED = "#ee2d2d"

class JSONifyable:
    @property
    def args(self): ...
    
    def jsonify(self): return {"__type": self.__class__.__name__, "args": self.args}

class UserError(Exception): ...

def handle_error(err: Exception) -> tuple[str, bool]:
    """
    :param Exception err: The raised exception

    :return: `error_message`, `handled`
    :rtype: tuple[str, bool]
    """
    handled = False
    if isinstance(err, UserError):
        error_message = str(err)
        handled = True
    else:
        traceback = err.__traceback__
        while traceback.tb_next: traceback = traceback.tb_next
        filename = os.path.split(traceback.tb_frame.f_code.co_filename)[1]
        line_number = traceback.tb_lineno
        error_message = f"{err.__class__.__name__} " \
                        f"({filename}, line {line_number}): {err}"
    if "`" not in error_message: error_message = f"`{error_message}`"
    return error_message, handled

def urlize(string):
    return re.sub(r"((https?://)?([\w\d-]+(\.[\w\d-]+)*(\.[\w\d-]{1,4})(/[^/\s]+)*)/?)", r"[\1](<https://\3>)", string)

def choicify(choices: list[str]):
    return [lightbulb.Choice(c, c) for c in choices]

T = TypeVar('T')
def list_to_groups(iterable: Iterable[T], group_size: int = 5) -> list[list[T]]:
    result = [[]]
    for element in iterable:
        if len(result[-1]) == group_size:
            result.append([])
        result[-1].append(element)
    return result

async def save_temporarily(callback, image: Image.Image | None, *args, **kwargs):
    if image is None:
        await callback(None, *args, **kwargs)
        return None
    temp_path = "temp"
    Path(temp_path).mkdir(parents=True, exist_ok=True)
    while True:
        filename = "".join(chr(random.randint(ord("a"), ord("z"))) for _ in range(8))
        path = os.path.join(temp_path, filename + ".png")
        if path not in os.listdir(temp_path): break
    image.save(path)
    await callback(path, *args, **kwargs)
    os.remove(path)
