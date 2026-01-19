from extensions.utils import JSONifyable
from json import JSONEncoder
from typing import Any
import re, inspect, sys

class MessageText:
    VAR_REGEX = r"\{\{\s*(\w+)\s*\}\}"

    def __init__(self, text: str):
        self.__raw = text
        self.__variables: list[str] = []
        self.__update_variables()
    
    def __update_variables(self):
        if re.findall(self.VAR_REGEX.replace(r"\w+", r"\S*[^\w\s]\S*"), self.__raw):
            raise ValueError("Forbidden variable name. Variable names can only consist of letters, digits and underscores (_)")
        self.__variables = set(re.findall(self.VAR_REGEX, self.__raw))
    
    @property
    def raw(self): return self.__raw

    @raw.setter
    def raw(self, value):
        self.__raw = value
        self.__update_variables()

    @property
    def variables(self): return self.__variables

    def with_values(self, **variable_values):
        provided_variables = set(variable_values.keys())
        if not provided_variables.issuperset(self.__variables):
            missing_vars = {f"'{var}'" for var in self.__variables-provided_variables}
            raise TypeError(f"Missing one or several variable values: {', '.join(missing_vars)}")
        text = self.__raw
        variable_values = {n: (v.value if isinstance(v, Variable) else v) for n, v in variable_values.items()}
        return re.sub(
            self.VAR_REGEX.replace(r"\w+", "|".join(variable_values.keys())),
            lambda match: variable_values[match.group(1)],
            text
        )

class Message(JSONifyable):
    def __init__(
            self, name: str, text: str | MessageText, channel_id: int = None, id: int = None, 
            og_author: int = None, last_editor: int = None
            ):
        self.name = name
        self.__text = MessageText("")
        self.text = text
        self.id = id
        self.channel_id = channel_id
        self.og_author = og_author
        self.last_editor = last_editor

    @property
    def text(self) -> MessageText: return self.__text

    @text.setter
    def text(self, value: str | MessageText): self.__text = value if isinstance(value, MessageText) else MessageText(value)

    @property
    def args(self):
        args = [self.name, self.text.raw, self.channel_id, self.id]
        if self.og_author: args.append(self.og_author)
        if self.last_editor: args.append(self.last_editor)
        return args

    def url(self, guild_id: int):
        return f"https://discord.com/channels/{guild_id}/{self.channel_id}/{self.id}"

class Variable(JSONifyable):
    def __init__(self, name: str, value: str = None):
        self.name = name
        self.value = value if value is not None else "`{{" + name + "}}`"
    
    @property
    def args(self): return [self.name, self.value]

    def __str__(self):
        result = f"`{self.name}` ="
        if set("`\n") & set(self.value): result += f"\n```\n{self.value}\n```"
        else: result += f" `{self.value}`"
        return result

cls_members = dict(inspect.getmembers(sys.modules[__name__], inspect.isclass))

def message_json_decode_hook(json_object):
    if type(json_object) in cls_members.values(): return json_object
    if hasattr(json_object, "__iter__") and "__type" in json_object:
        this_class = cls_members[json_object["__type"]]
        args = json_object["args"] # [message_json_decode_hook(x) for x in json_object["args"]]
        return this_class(*args)
    return json_object

class MessageJSONEncoder(JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (Message, Variable)):
            return o.jsonify()
        else:
            return super().default(o)
