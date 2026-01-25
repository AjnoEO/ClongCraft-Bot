"""
Supervising

- Welcome messages
- Maintaining the separation of Clong and non-Clong contexts
"""

from configparser import ConfigParser
from extensions.utils import *
import extensions
import hikari, lightbulb, miru, os

if os.path.exists("config.ini"):
    config = ConfigParser()
    config.read("config.ini")
else:
    raise FileExistsError("config.ini is missing.\n"
                          "If you cloned or pulled the git repo, "
                          "make sure to copy example.config.ini, "
                          "name it config.ini and edit for your needs.")


bot = hikari.GatewayBot(
    token=config["data"]["token"],
    # help_class=None,
    intents=hikari.Intents.ALL_UNPRIVILEGED
    | hikari.Intents.MESSAGE_CONTENT
    | hikari.Intents.GUILD_MEMBERS,
)
lightbulb_client = lightbulb.client_from_app(bot)
miru_client = miru.Client(bot, ignore_unknown_interactions=True)
lightbulb_client.di.registry_for(
    lightbulb.di.Contexts.DEFAULT
).register_value(miru.Client, miru_client)

@bot.listen(hikari.StartingEvent)
async def on_starting(_: hikari.StartingEvent) -> None:
    await lightbulb_client.load_extensions_from_package(extensions)
    await lightbulb_client.start()

@lightbulb_client.error_handler
async def handler(exc: lightbulb.exceptions.ExecutionPipelineFailedException) -> bool:
    """Error handler"""
    if exc.pipeline.invocation_failed:
        error_cause = exc.invocation_failure
    else:
        error_cause = exc.hook_failures[0]
    error_message, handled = handle_error(error_cause)
    embed = hikari.Embed(
        title = "Error!",
        description = f"An error occurred while attempting to use `/{exc.context.command_data.name}`.\n"
                      f"Error message: {error_message}",
        color = RED
    )
    await exc.context.respond(embed, ephemeral=True)
    return handled


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
