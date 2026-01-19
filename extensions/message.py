"""
Admin messages

Admin messages can be sent and edited through the bot by any administrator
"""

from .utils.message import Message, Variable, message_json_decode_hook, MessageJSONEncoder
from .utils.paginator import PaginatorView
from .utils.utils import UserError, handle_error, RED
import json
from json import JSONDecoder
import os
import hikari, lightbulb, miru

import requests
from asyncio import sleep
from datetime import datetime, timezone

loader = lightbulb.Loader()

messages: dict[str, Message] = {}
variables: dict[str, Variable] = {}
var_to_msg: dict[str, list[str]] = {}

if os.path.exists("messages.json"):
    with open("messages.json", encoding="utf-8") as f:
        data = JSONDecoder(object_hook=message_json_decode_hook).decode(f.read())
    messages = {m.name: m for m in data["messages"]}
    variables = {v.name: v for v in data["variables"]}

def update_var_to_msg():
    global var_to_msg
    var_to_msg = {}
    for msg_name, msg in messages.items():
        for var_name in msg.text.variables:
            var_to_msg.setdefault(var_name, [])
            var_to_msg[var_name].append(msg_name)
    for var_name in list(variables.keys()):
        if not var_name in var_to_msg:
            del variables[var_name]

update_var_to_msg()

def save_message_data():
    with open("messages.json", "w") as f:
        json.dump({
            "messages": list(messages.values()),
            "variables": list(variables.values())
        }, f, cls = MessageJSONEncoder, indent = 4)
    update_var_to_msg()

@loader.listener(hikari.StartedEvent)
async def on_starting(event: hikari.StartedEvent) -> None:
    for name, msg in messages.items():
        try: await event.app.rest.fetch_message(msg.channel_id, msg.id)
        except hikari.NotFoundError: del messages[name]
        save_message_data()

CHARACTER_LIMIT = 2000

metadata_path = os.path.join("meta.json")
if os.path.exists(metadata_path):
    with open(metadata_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        GUILD_ID: int = data["Guild ID"]
        # WELCOME_CHANNEL: hikari.GuildChannel = data["Welcome channel ID"]
        # WELCOME_MESSAGE: str = data["Welcome message"]
        # NO_TEXT_CATEGORIES: List[int] = data["No-text categories"]
        SERVER_RESTART_HOUR: int = data["Server restart hour"]
        SERVER_RESTART_MINUTE: int = data["Server restart minute"]
        MAX_EMOJIS: int = data["Max custom emojis"]
        EMOJIS_PER_MESSAGE: int = data["Emojis per message"]
        PROTECTED_EMOJIS: int = data["Emojis protected by vote"]
else:
    raise FileNotFoundError("meta.json is missing.\n"
                            "If you cloned or pulled the git repo, "
                            "make sure to copy example.meta.json, "
                            "name it meta.json and edit for your needs.")

async def process_emoji_vote(message: hikari.Message):
    if "emoji_vote" not in messages:
        return
    emoji_vote_channel = messages["emoji_vote"].channel_id
    if message.channel_id != emoji_vote_channel:
        return
    # The message was in the emoji vote channel, attempt to count it as a vote
    bot = message.app
    for att in message.attachments:
        try:
            emoji = await bot.rest.create_emoji(guild=GUILD_ID, name=f"clong_{message.author.id}_{message.id%10000}", image=att)
        except:
            continue
        # Get all existing emojis
        reactions = []
        messages_containing_emoji = {}
        message_with_room = None
        async for msg in bot.rest.fetch_messages(emoji_vote_channel):
            if not msg.author.is_bot:
                continue
            # Collect all the reactions
            for react in msg.reactions:
                reactions.append(react)
                # Track the message each emoji was contained in
                messages_containing_emoji[react.emoji.id] = msg
            # Place new emojis in the first message that has room for additional emojis
            if len(msg.reactions) < EMOJIS_PER_MESSAGE:
                message_with_room = msg
        # If we are at max emojis, we need to remove an emoji
        if len(reactions) == MAX_EMOJIS:
            # Sort by vote count
            sorted_reactions = sorted(reactions, key = lambda x: x.count, reverse=True)
            # Take out the top emojis (protected by vote) leaving only the ones low enough in votes to be replaced
            unprotected = sorted_reactions[PROTECTED_EMOJIS:-1]
            # Find the oldest emoji (this is so we don't always replace the emoji with a single vote,
            # and cycle between a set of most recent emojis to give them time to be voted on)
            oldest = min(*unprotected, key = lambda x: x.emoji.created_at).emoji
            # Place the new emoji where the old one was
            message_with_room = messages_containing_emoji[oldest.id]
            # Delete the oldest emoji
            await bot.rest.delete_all_reactions_for_emoji(emoji_vote_channel, message_with_room, oldest.name, oldest.id)
            await bot.rest.delete_emoji(GUILD_ID, oldest.id)
        # If no messages have room for the emoji, make a new message
        if not message_with_room:
            message_with_room = await bot.rest.create_message(emoji_vote_channel, ".")
        # Add the new emoji and its reaction vote
        await bot.rest.add_reaction(emoji_vote_channel, message_with_room, emoji)
    # Delete the user's message that added the emoji
    await message.delete()


@loader.listener(hikari.GuildReactionAddEvent)
async def on_reaction_add(event: hikari.GuildReactionAddEvent) -> None:
    # Handle votes in the emoji vote
    if "emoji_vote" not in messages:
        return
    emoji_vote_channel = messages["emoji_vote"].channel_id
    if event.channel_id == emoji_vote_channel:
        emoji_parts = event.emoji_name.split("_")
        emoji_creator = emoji_parts[1]
        if emoji_creator == str(event.user_id):
            # The person who initially made the emoji voted for it
            # To keep the votes accurate, the bot's vote will now be removed
            await event.app.rest.delete_my_reaction(event.channel_id, event.message_id, event.emoji_name, event.emoji_id)

@loader.listener(hikari.GuildReactionDeleteEvent)
async def on_reaction_remove(event: hikari.GuildReactionDeleteEvent) -> None:
    bot = event.app
    if "emoji_vote" not in messages:
        return
    emoji_vote_channel = messages["emoji_vote"].channel_id
    if event.channel_id == emoji_vote_channel:
        async for user in bot.rest.fetch_reactions_for_emoji(emoji_vote_channel, event.message_id, event.emoji_name, event.emoji_id):
            break
        else:
            # Emoji has been fully removed - delete it
            await bot.rest.delete_emoji(GUILD_ID, event.emoji_id)

@loader.listener(hikari.MessageCreateEvent)
async def on_message_create(event: hikari.MessageCreateEvent) -> None:
    if event.is_bot:
        return
    message = event.message
    await process_emoji_vote(message)

@loader.listener(hikari.MessageDeleteEvent)
async def on_message_delete(event: hikari.MessageDeleteEvent) -> None:
    for name, msg in messages.items():
        if msg.channel_id == event.channel_id and msg.id == event.message_id:
            del messages[name]
            save_message_data()
            return


@loader.command
class Emoji(
    lightbulb.SlashCommand,
    name="look-up-emoji",
    description="Look up who made an emoji",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR,
):
    emoji = lightbulb.string(
        "emoji",
        "Emoji to look up. You can insert the emoji itself, its name, or its ID.",
    )

    @lightbulb.invoke
    async def look_up_emoji(self, ctx: lightbulb.Context) -> None:
        string = self.emoji.strip().split(":")[-1].split(">")[0]
        try:
            id = int(string)
        except:
            return await ctx.respond(f"Unrecognized emoji ID", ephemeral = True)

        emoji = await ctx.client.rest.fetch_emoji(GUILD_ID, id)
        if not emoji.name.startswith("clong_"):
            return await ctx.respond(f"Not a Clong emoji", ephemeral = True)
            
        creator_id = emoji.name.split("_")[1]
        return await ctx.respond(f"That emoji was created by <@{creator_id}>", ephemeral = True)

@loader.command
class DeleteEmoji(
    lightbulb.SlashCommand,
    name="delete-emoji",
    description="Delete a problematic emoji",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR,
):
    emoji = lightbulb.string(
        "emoji",
        "Emoji to delete. You can insert the emoji itself, or its ID.",
    )

    @lightbulb.invoke
    async def delete_emoji(self, ctx: lightbulb.Context) -> None:
        string = self.emoji.strip().split(":")[-1].split(">")[0]
        try:
            id = int(string)
        except:
            return await ctx.respond(f"Unrecognized emoji ID", ephemeral = True)

        bot = ctx.client

        emoji = await bot.rest.fetch_emoji(GUILD_ID, id)
        if not emoji.name.startswith("clong_"):
            return await ctx.respond(f"Not a Clong emoji", ephemeral = True)
            
        creator_id = emoji.name.split("_")[1]

        if "emoji_vote" in messages:
            emoji_vote_channel = messages["emoji_vote"].channel_id
            # Get all existing emojis
            messages_containing_emoji = {}
            async for msg in bot.rest.fetch_messages(emoji_vote_channel):
                if not msg.author.is_bot:
                    continue
                # Collect all the reactions
                for react in msg.reactions:
                    # Track the message each emoji was contained in
                    messages_containing_emoji[react.emoji.id] = msg
            message = messages_containing_emoji[id]
            await bot.rest.delete_all_reactions_for_emoji(emoji_vote_channel, message, emoji.name, id)
        await bot.rest.delete_emoji(GUILD_ID, id)

        return await ctx.respond(f"Deleted the emoji. That emoji was created by <@{creator_id}>", ephemeral = True)


message_cmd_group = lightbulb.Group(
    "message", 
    "Admin message commands", 
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
)
loader.command(message_cmd_group)

async def message_name_autocomplete(ctx: lightbulb.AutocompleteContext[str]) -> None:
    input_data = ctx.focused.value
    names = [name for name in messages.keys() if name.startswith(input_data)]
    names += [name for name in messages.keys() if not name.startswith(input_data) and input_data in name]
    if len(names) > 25: names = names[:25]
    await ctx.respond(names)
    return


async def create_message(channel: hikari.TextableChannel, name: str, text: str, user_id: int):
    if len(text) > CHARACTER_LIMIT:
        raise UserError(f"The message length cannot exceed {CHARACTER_LIMIT} characters")
    msg = Message(name, text, channel.id, og_author=user_id)
    for var in msg.text.variables:
        if var not in variables:
            variables[var] = Variable(var)
    text = msg.text.with_values(**variables)
    message = await channel.app.rest.create_message(channel, text)
    msg.id = message.id
    messages[name] = msg
    save_message_data()
    return f"New message `{msg.name}` created: {msg.url(GUILD_ID)}"

message_creation_processes: dict[int, tuple[hikari.TextableChannel, str]] = {}

class CreateModal(miru.Modal, title="Create Admin Message"):
    text = miru.TextInput(
        label="Message text",
        style=hikari.TextInputStyle.PARAGRAPH,
        placeholder="Use {{variable_name}} to declare variables",
        required=True
    )

    async def callback(self, ctx: miru.ModalContext) -> None:
        await ctx.defer()
        await ctx.respond(
            await create_message(*message_creation_processes.pop(ctx.user.id), self.text.value, ctx.user.id),
            flags=hikari.MessageFlag.EPHEMERAL
        )

    async def on_error(self, error: Exception, ctx: miru.ViewContext) -> None:
        error_message, handled = handle_error(error)
        embed = hikari.Embed(
            title = "Error!",
            description = f"An error occurred while creating admin message.\n"
                          f"Error message: {error_message}",
            color = RED
        )
        if ctx is not None:
            await ctx.respond(embed, ephemeral=True)
        else: raise error
        if not handled: raise error

@message_cmd_group.register
class message_create(
    lightbulb.SlashCommand,
    name="create",
    description="Create an admin message"
):
    channel = lightbulb.channel(
        "channel", "The channel to send the message to", channel_types=[
            hikari.ChannelType.GUILD_TEXT,
            hikari.ChannelType.GUILD_PRIVATE_THREAD,
            hikari.ChannelType.GUILD_PUBLIC_THREAD,
            hikari.ChannelType.GUILD_NEWS_THREAD,
            hikari.ChannelType.GUILD_NEWS
        ]
    )
    name = lightbulb.string(
        "name", "The name of the message to refer to later when editing it"
    )

    @lightbulb.invoke
    @lightbulb.di.with_di
    async def message_create(self, ctx: lightbulb.Context, miru_client: miru.Client = lightbulb.di.INJECTED) -> None:
        if self.name in messages:
            raise UserError(f"There is already a message with name `{self.name}`: {messages[self.name].url(GUILD_ID)}")
        message_creation_processes[ctx.user.id] = (self.channel, self.name)
        modal = CreateModal(title=f"Create Admin Message: {self.name}")
        builder = modal.build_response(miru_client)
        await builder.create_modal_response(ctx.interaction)
        miru_client.start_modal(modal)
        return


async def edit_message(bot: lightbulb.Client, name: str, text: str, user_id: int):
    if len(text) > CHARACTER_LIMIT:
        raise UserError(f"The message length cannot exceed {CHARACTER_LIMIT} characters")
    msg = messages[name]
    msg.text = text
    msg.last_editor = user_id
    for var_name in msg.text.variables:
        if var_name not in variables:
            variables[var_name] = Variable(var_name)
    save_message_data()
    await bot.rest.edit_message(msg.channel_id, msg.id, msg.text.with_values(**variables))
    return f"Edited message `{msg.name}` {msg.url(GUILD_ID)}"

message_editing_processes: dict[int, str] = {}

class EditModal(miru.Modal, title="Edit Admin Message"):
    text = miru.TextInput(
        label="Message text. {{variable_name}} for variables",
        style=hikari.TextInputStyle.PARAGRAPH,
        placeholder="Use {{variable_name}} to declare variables",
        required=True
    )

    async def callback(self, ctx: miru.ModalContext) -> None:
        await ctx.defer()
        await ctx.respond(
            await edit_message(ctx.client, message_editing_processes.pop(ctx.user.id), self.text.value, ctx.user.id),
            flags=hikari.MessageFlag.EPHEMERAL
        )

    async def on_error(self, error: Exception, ctx: miru.ViewContext) -> None:
        error_message, handled = handle_error(error)
        embed = hikari.Embed(
            title = "Error!",
            description = f"An error occurred while editing admin message.\n"
                          f"Error message: {error_message}",
            color = RED
        )
        if ctx is not None:
            await ctx.respond(embed, flags=hikari.MessageFlag.EPHEMERAL)
        else: raise error
        if not handled: raise error

@message_cmd_group.register
class message_edit(
    lightbulb.SlashCommand,
    name="edit",
    description="Edit an admin message"
):
    name = lightbulb.string(
        "name", "The name of the message to edit", autocomplete=message_name_autocomplete
    )

    @lightbulb.invoke
    @lightbulb.di.with_di
    async def message_edit(self, ctx: lightbulb.Context, miru_client: miru.Client = lightbulb.di.INJECTED) -> None:
        message_editing_processes[ctx.user.id] = self.name
        modal = EditModal(title=f"Edit Admin Message: {self.name}")
        modal.text.value = messages[self.name].text.raw
        builder = modal.build_response(miru_client)
        await builder.create_modal_response(ctx.interaction)
        miru_client.start_modal(modal)
        return
    

@message_cmd_group.register
class message_unlink(
    lightbulb.SlashCommand,
    name="unlink",
    description="Unlink an admin message without deleting it"
):
    name = lightbulb.string(
        "name", "The name of the message to unlink", autocomplete=message_name_autocomplete
    )

    @lightbulb.invoke
    async def message_unlink(self, ctx: lightbulb.Context) -> None:
        msg =  messages.pop(self.name)
        save_message_data()
        await ctx.respond(f"Unlinked message `{msg.name}` {msg.url(GUILD_ID)}", ephemeral=True)


@message_cmd_group.register
class message_delete(
    lightbulb.SlashCommand,
    name="delete",
    description="Delete an admin message"
):
    name = lightbulb.string(
        "name", "The name of the message to delete", autocomplete=message_name_autocomplete
    )

    @lightbulb.invoke
    async def message_delete(self, ctx: lightbulb.Context) -> None:
        msg = messages[self.name]
        await ctx.client.rest.delete_message(msg.channel_id, msg.id, reason=f"Deleted by admin <@{ctx.user.id}>")
        del messages[self.name]
        save_message_data()
        await ctx.respond(f"Deleted message `{msg.name}`", ephemeral=True)


MESSAGES_PER_LIST_PAGE = 15


def list_messages(page: int) -> tuple[str, int]:
    if not messages:
        return "There are no admin messages right now", 1
    count = len(messages)
    max_page = (count - 1) // MESSAGES_PER_LIST_PAGE + 1
    if page > max_page: raise UserError(f"Cannot display page {page}. The last page is {max_page}")
    response = "There is 1 admin message:" if len(messages) == 1 else f"There are {count} admin messages:"
    for msg in list(messages.values())[ (page-1)*MESSAGES_PER_LIST_PAGE : page*MESSAGES_PER_LIST_PAGE ]:
        response += f"\n- `{msg.name}` {msg.url(GUILD_ID)}"
    if max_page > 1: response += f"\n(page {page}/{max_page})"
    return response, max_page


@message_cmd_group.register
class message_list(
    lightbulb.SlashCommand,
    name="list",
    description="List the admin messages"
):
    page = lightbulb.integer(
        "page", "The page to display", default=1
    )
    for_everyone = lightbulb.boolean(
        "for_everyone", "Set to true to send to everyone", default=False
    )

    @lightbulb.invoke
    @lightbulb.di.with_di
    async def message_list(self, ctx: lightbulb.Context, miru_client: miru.Client = lightbulb.di.INJECTED) -> None:
        response, max_page = list_messages(self.page)
        if max_page == 1:
            await ctx.respond(response, ephemeral = not self.for_everyone)
            return
        view = PaginatorView(self.page, max_page, list_messages)
        await ctx.respond(response, components=view, ephemeral = not self.for_everyone)
        miru_client.start_view(view)


@message_cmd_group.register
class message_info(
    lightbulb.SlashCommand,
    name="info",
    description="View info about an admin message"
):
    name = lightbulb.string(
        "name", "The name of the message to delete", autocomplete=message_name_autocomplete
    )
    for_everyone = lightbulb.boolean(
        "for_everyone", "Set to true to send to everyone", default=False
    )

    @lightbulb.invoke
    async def message_info(self, ctx: lightbulb.Context) -> None:
        msg = messages[self.name]
        response = f"### Message `{msg.name}` {msg.url(GUILD_ID)}"
        if msg.og_author:
            response += f"\nOriginal author: <@{msg.og_author}>"
        if msg.last_editor:
            response += f"\nLast edited by <@{msg.last_editor}>"
        if msg.text.variables:
            response += "\nVariables:"
            for var_name in msg.text.variables:
                var = variables[var_name]
                response += f"\n- {var}"
        await ctx.respond(response, ephemeral = not self.for_everyone)


variable_cmd_subgroup = message_cmd_group.subgroup(
    "variable",
    "Commands for managing variables in admin messages"
)

async def variable_name_autocomplete(ctx: lightbulb.AutocompleteContext[str]) -> None:
    input_data = ctx.focused.value
    names = [name for name in variables.keys() if name.startswith(input_data)]
    names += [name for name in variables.keys() if not name.startswith(input_data) and input_data in name]
    if len(names) > 25: names = names[:25]
    await ctx.respond(names)
    return


@variable_cmd_subgroup.register
class variable_set(
    lightbulb.SlashCommand,
    name="set",
    description="Set the variable value and update the corresponding messages"
):
    name = lightbulb.string(
        "name", "The name of the variable to edit", autocomplete=variable_name_autocomplete
    )
    value = lightbulb.string(
        "value", "New value for the variable"
    )

    @lightbulb.invoke
    async def variable_set(self, ctx: lightbulb.Context):
        await ctx.defer(ephemeral=True)
        var = variables[self.name]
        var.value = self.value
        for msg_name in var_to_msg[var.name]:
            msg = messages[msg_name]
            await ctx.client.rest.edit_message(msg.channel_id, msg.id, msg.text.with_values(**variables))
        save_message_data()
        response = f"Set variable value: {var}"
        if self.name in var_to_msg:
            msg_count = len(var_to_msg[self.name])
            response += "\n1 message was updated" if msg_count == 1 else f"\n{msg_count} messages were updated"
        await ctx.respond(response, ephemeral=True)


@variable_cmd_subgroup.register
class variable_list(
    lightbulb.SlashCommand,
    name="list",
    description="List the variables used in admin messages"
):
    for_everyone = lightbulb.boolean(
        "for_everyone", "Set to true to send to everyone", default=False
    )

    @lightbulb.invoke
    async def message_list(self, ctx: lightbulb.Context) -> None:
        if not variables:
            await ctx.respond("There are no variables in admin messages right now", ephemeral = not self.for_everyone)
            return
        response = "There is 1 variable:" if len(variables) == 1 else f"There are {len(variables)} variables:"
        for var in variables.values(): response += f"\n- {var}"
        await ctx.respond(response, ephemeral = not self.for_everyone)


UPDATE_TIME_MINS = 1

@loader.task(lightbulb.uniformtrigger(seconds=UPDATE_TIME_MINS*60), True, -1, -1)
async def update_server_status(bot: hikari.GatewayBot) -> None:
    for key in variables:
        if key.startswith("ip"):
            name = key[2:]
            await update_server_status(bot, name)

async def update_server_status(bot: hikari.GatewayBot, name: str):
    # Get server ip
    address = variables[f"ip{name}"].value
    resp = requests.get(f"https://api.mcsrvstat.us/3/{address}").json()

    # Check current time against server restart time
    # This is because the server may restart fast enough for the 1-minute interval to miss it,
    # thus resulting in an inaccurate Uptime stat
    # Server restarts at the configured time UTC
    restart_hour = SERVER_RESTART_HOUR
    restart_minute = SERVER_RESTART_MINUTE

    current = datetime.now(timezone.utc)
    hourdiff = current.hour - restart_hour
    minutediff = current.minute - restart_minute

    # Calculate status variables
    online = "players" in resp
    online_readable = "online" if online else "offline"
    player_count = resp["players"]["online"] if online else 0
    player_count_pluralizer = "" if player_count==1 else "s"
    uptime = ((60 * 24) + hourdiff * 60 + minutediff) % (60 * 24)
    uptime_minutes = uptime % 60
    uptime_hours = uptime // 60
    player_list = "\n".join(p["name"] for p in resp["players"]["list"]) if player_count > 0 and "list" in resp["players"] else "None"
    # Update status variables
    vars_to_update = {f"status{name}_online": online, f"status{name}_online_readable": online_readable,
                      f"status{name}_player_count": player_count, f"status{name}_player_count_pluralizer": player_count_pluralizer,
                      f"status{name}_uptime_minutes": uptime_minutes, f"status{name}_uptime_hours": uptime_hours,
                      f"status{name}_player_list": player_list}
    messages_to_update = set()
    for key in vars_to_update:
        if key in variables:
            var = variables[key]
            var.value = str(vars_to_update[key])
            for msg_name in var_to_msg[var.name]:
                messages_to_update.add(msg_name)
    for msg_name in messages_to_update:
        msg = messages[msg_name]
        await bot.rest.edit_message(msg.channel_id, msg.id, msg.text.with_values(**variables))
    save_message_data()
    # Update status channel
    if f"status{name}" in messages:
        await sleep(1)
        msg = messages[f"status{name}"]
        status_channel_name = f"🟢-{player_count}-player{player_count_pluralizer}-online" if online else "🔴-server-offline"
        await bot.rest.edit_channel(msg.channel_id,name=status_channel_name)
