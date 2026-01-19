import json
import os
import re
import hikari, lightbulb

loader = lightbulb.Loader()

if os.path.exists("meta.json"):
    with open("meta.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        WELCOME_CHANNEL: hikari.GuildChannel = data["Welcome channel ID"]
        WELCOME_MESSAGE: str = data["Welcome message"]
        NO_TEXT_CATEGORIES: list[int] = data["No-text categories"]
else:
    raise FileNotFoundError("meta.json is missing.\n"
                            "If you cloned or pulled the git repo, "
                            "make sure to copy example.meta.json, "
                            "name it meta.json and edit for your needs.")

@loader.listener(hikari.MemberCreateEvent)
async def on_join(event: hikari.MemberCreateEvent) -> None:
    message = WELCOME_MESSAGE.format(mention=event.member.mention)
    channel = WELCOME_CHANNEL
    await event.app.rest.create_message(channel, message)

async def is_clong_channel(channel: hikari.GuildChannel) -> bool:
    parent_id = channel.parent_id
    if isinstance(channel, hikari.GuildThreadChannel):
        # If the channel is a thread, we need to go up two levels, first to the parent channel, then to the parent category
        channel = await channel.app.rest.fetch_channel(parent_id)
        parent_id = channel.parent_id
    return parent_id in NO_TEXT_CATEGORIES

async def delete_if_necessary(message: hikari.Message):
    if not message.content:
        return
    text = message.content

    if message.type == 18: # THREAD_CREATED
        return

    channel: hikari.GuildChannel = await message.fetch_channel()
    if channel.type not in [hikari.ChannelType.GUILD_TEXT, hikari.ChannelType.GUILD_VOICE,
                            hikari.ChannelType.GUILD_PRIVATE_THREAD, hikari.ChannelType.GUILD_PUBLIC_THREAD]:
        return
    is_clong = await is_clong_channel(channel)

    # Filter out Minecraft emojis (non-meta in both contexts)
    text = re.sub(r"<:mc_[a-zA-Z0-9_]*:[0-9]+>", "", text)
    if re.search(r"<:clong_[a-zA-Z0-9_]*:[0-9]+>", text):
        # Contains Clong emoji
        if not is_clong:
            # Delete Clong emojis in normal channels
            return await message.delete()
        # Filter out Clong emojis
        text = re.sub(r"<:clong_[a-zA-Z0-9_]*:[0-9]+>", "", text)
    if re.search(r"<:[a-zA-Z0-9_]*:[0-9]+>", text):
        # Contains non-Clong emoji
        if is_clong:
            # Delete non-Clong emojis in Clong channels
            return await message.delete()

    text = re.sub(r"<(@|#|@&)\d+?>", "", text)
    text = re.sub(r"https?://[A-Za-z0-9-]+\.[A-Za-z0-9.-]+(/\S+)?", "", text)
    if re.match(r"\s*$", text):
        return
    if is_clong:
        await message.delete()

@loader.listener(hikari.GuildReactionAddEvent)
async def on_reaction_add(event: hikari.GuildReactionAddEvent) -> None:
    bot = event.app
    channel: hikari.GuildChannel = await bot.rest.fetch_channel(event.channel_id)
    is_clong_category = await is_clong_channel(channel)
    is_clong_emoji = event.emoji_name.startswith("clong_")
    # Delete emoji if it is not used in the right place

    if is_clong_category != is_clong_emoji and not event.emoji_name.startswith("mc_"):
        msg = await bot.rest.fetch_message(event.channel_id, event.message_id)
        old_react = False
        for react in msg.reactions:
            if event.is_for_emoji(react.emoji):
                # Don't remove if the emoji is not the first one added (the old reactions are not banned)
                if react.count > 1: old_react = True
                break
        if not old_react:
            isunicode = isinstance(event.emoji_name, hikari.UnicodeEmoji)
            if isunicode:
                await bot.rest.delete_all_reactions_for_emoji(event.channel_id, event.message_id, event.emoji_name)
            else:
                await bot.rest.delete_all_reactions_for_emoji(event.channel_id, event.message_id, event.emoji_name, event.emoji_id)
        

@loader.listener(hikari.MessageCreateEvent)
async def on_message_create(event: hikari.MessageCreateEvent) -> None:
    if event.is_bot:
        return
    message = event.message
    await delete_if_necessary(message)

@loader.listener(hikari.MessageUpdateEvent)
async def on_message_edit(event: hikari.MessageUpdateEvent) -> None:
    if event.is_bot:
        return
    message = event.message
    await delete_if_necessary(message)
