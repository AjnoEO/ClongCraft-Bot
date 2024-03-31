from enum import Enum
from typing import List, Callable, Optional

SplitFunc = Callable[[str, List[str]], Optional[List[str]]]

class SplitMode(Enum):
    No = "Do not split"
    Longest = "Split matching longest first"
    Single = "Split if unambiguous"

    def __init__(self, value) -> None:
        super().__init__()
        self.__index: int = len(self.__class__)
        self.split: Optional[SplitFunc] = None

    @property
    def index(self) -> int: return self.__index

def splitter(split_mode: SplitMode):
    def __inner(func: SplitFunc):
        split_mode.split = func
        return func
    return __inner

@splitter(SplitMode.No)
def split(text: str, names: List[str]) -> Optional[List[str]]:
    return [text]

@splitter(SplitMode.Longest)
def split(text: str, names: List[str]) -> Optional[List[str]]:
    if not text: return []
    for name in sorted(names, key = len, reverse = True):
        if text.startswith(name):
            rest = SplitMode.Longest.split(text[len(name):], names)
            if rest is not None:
                return [name] + rest
    return None

@splitter(SplitMode.Single)
def split(text: str, names: List[str]) -> Optional[List[str]]:
    splits = all_splits(text, names)
    return splits[0] if len(splits) == 1 else (None if splits else [text])

def all_splits(text: str, names: List[str]) -> List[List[str]]:
    output = _all_splits(text, names)
    if len(output) == 1 and len(output[0]) == 0: return []
    return output

def _all_splits(text: str, names: List[str]) -> List[List[str]]:
    if not text: return [[]]
    output = []
    for name in sorted(names, key = len, reverse = True):
        if text.startswith(name):
            rest = _all_splits(text[len(name):], names)
            output += [[name] + x for x in rest]
    return output