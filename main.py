import discord
from music_cog import music_cog
from discord.ext import commands
import json


pref = "!"
activity = discord.Game(name = "!help")
bot = commands.Bot(command_prefix=pref, activity = activity)

#remove the default help command so that we can write out own
bot.remove_command('help')

#register the class with the bot
bot.add_cog(music_cog(bot, pref))


#open keys.json in dictionary 'keys'
with open("keys.json", "r") as keys_json:
    keys = json.load(keys_json)

TOKEN = keys['API']["discord"]
bot.run(TOKEN)
