#built in modules
import random #used to shuffle playlist
import asyncio #used to run async function in non-async function

#external modules
import discord
from discord.ext import commands

#self defined modules
from youtubeapi import get_playlist_details, get_id, get_audio_url, get_video_details, get_video_details_id #for searching and url finding purposes


class music_cog(commands.Cog):
    def __init__(self, bot, pref):
        self.bot = bot
        self.pref = pref
        self.help_message = [
            {
                "name" : "General commands:",
                "value" : "**{0}h** - displays all the available commands".format(pref)
            },
            {
                "name" : "Music commands:",
                "value" : "**{0}p <keywords>** - finds the song on youtube and plays it in your current channel\n**{0}q** - displays the current music queue\n**{0}s** - skips the current song being played\n**{0}d** - disconnects bot from current voice channel\n**{0}sf** - shuffle music queue\n**{0}clr** - clear music queue\n**{0}rm <index>** - remove song in <index> position in queue\n**{0}m <song index> <target index>** - move song from <song index> to <target index> in queue".format(pref)
            }

        ]


    #data structures to keep track of state of bot in individual servers
    voice_channel = {} #keep track of the voice channel the bot needs to join when first called
    text_channel = {} #keep track of the last text channel where a command is called
    current_song = {} #keep track of the current song that the bot is playing
    music_queue = {} #keep track of the music queue 
    is_playing = {} #keep track of whether or not the bot is currently playing in a server
    vclient = {} #keep track of the voice client being used in a server
    queue_msg = {} #keep track of the queue message details when going to next or last page
    
    
    SONGS_PER_PAGE = 6 #constant to keep track of the number of songs to display per page when queue is shown
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'} #ffmpeg option for playing audio

#---------------------------------------------------------------------------
#------------------------------general funcs--------------------------------
#---------------------------------------------------------------------------
    #deletes messages
    async def delete_message(self, channel, id):
        await channel.delete_messages([discord.Object(id=id)])


    #used to go to next page or previous page when reaction is clicked on latest queue message
    async def flip_page(self, svr_id, direction):

        #initiate embed message to be sent
        em = discord.Embed()

        #embed current song details to message
        title = self.current_song[svr_id]["title"]
        id = self.current_song[svr_id]["id"]
        em.add_field(name="Currently playing", value="[**{0}**](https://www.youtube.com/watch?v={1})\n".format(title, id), inline=False)
        
        #add x number of songs under title "coming next" depending on self.SONGS_PER_PAGE
        name = "Coming up next:"
        val = ""
        queue_len = len(self.music_queue[svr_id])
        prev_start = self.queue_msg[svr_id]["prev_last"]-self.SONGS_PER_PAGE
        prev_last = self.queue_msg[svr_id]["prev_last"]
        print(prev_start)
        msg = self.queue_msg[svr_id]["msg"]

        #for going to previous page
        if direction == 0:

            #when current page is 2nd to large page, go to previous page
            if prev_start >= self.SONGS_PER_PAGE: 
                #add x number of songs to empty string "val"
                for i in range(prev_start-self.SONGS_PER_PAGE, prev_start):
                    title = self.music_queue[svr_id][i]["title"]
                    id = self.music_queue[svr_id][i]["id"]
                    val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)

                #embed the next songs in queue to message
                em.add_field(name=name, value=val, inline=False)

                #edit the latest queue message with updated message
                await msg.edit(embed=em)

                #to keep track of what page queue message is on
                self.queue_msg[svr_id]['prev_last'] = prev_start
                
            #when current page is 1st page, go to last page    
            elif prev_start == 0: 
                #decide the index of the 1st song to be shown on current page of queue
                nb_of_songs_in_last = queue_len%self.SONGS_PER_PAGE
                if nb_of_songs_in_last == 0:
                    start = queue_len - self.SONGS_PER_PAGE
                else:    
                    start = queue_len - nb_of_songs_in_last
                
                #add x number of songs to empty string "val"
                for i in range(start, queue_len):
                    title = self.music_queue[svr_id][i]["title"]
                    id = self.music_queue[svr_id][i]["id"]
                    val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)

                #embed the next songs in queue to message and edit previous queue message
                em.add_field(name=name, value = val, inline = False)
                await msg.edit(embed=em)
                self.queue_msg[svr_id]['prev_last'] = start+self.SONGS_PER_PAGE

        #for going to next page
        elif direction == 1:

            #when current page is 1st page to 2nd last page
            if queue_len > prev_last+self.SONGS_PER_PAGE:
                for i in range(prev_last, prev_last+self.SONGS_PER_PAGE):
                    title = self.music_queue[svr_id][i]["title"]
                    id = self.music_queue[svr_id][i]["id"]
                    val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)

                em.add_field(name=name, value = val, inline = False)
                await msg.edit(embed=em)
                self.queue_msg[svr_id]['prev_last'] = prev_last+self.SONGS_PER_PAGE

            #when current page is last page
            elif prev_last >= queue_len:
                start = 0
                last = self.SONGS_PER_PAGE
                for i in range(start, last):
                    title = self.music_queue[svr_id][i]["title"]
                    id = self.music_queue[svr_id][i]["id"]
                    val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)
                
                em.add_field(name=name, value = val, inline = False)
                await msg.edit(embed=em)
                self.queue_msg[svr_id]['prev_last'] = self.SONGS_PER_PAGE

            #not sure what this part is for, do further testing to check if it is needed
            else:
                for i in range(prev_last, queue_len):
                    title = self.music_queue[svr_id][i]["title"]
                    id = self.music_queue[svr_id][i]["id"]
                    val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)
                
                em.add_field(name=name, value = val, inline = False)
                await msg.edit(embed=em)
                self.queue_msg[svr_id]['prev_last'] = prev_last+self.SONGS_PER_PAGE


    #reset state of bot to initial state
    def reset(self, svr_id):
        self.voice_channel[svr_id] = None
        self.text_channel[svr_id] = None
        self.current_song[svr_id] = None
        self.is_playing[svr_id] = False
        self.vclient[svr_id] = None
        self.music_queue[svr_id] = []
        
        

    #send help message to text channel
    async def show_help(self, channel, ttl="Tune Bot Commands"):
        em = discord.Embed(title=ttl)
        for i in self.help_message:
            name = i["name"]
            val = i["value"] + "\n\n"       
            em.add_field(name=name, value=val, inline=False)

        await channel.send(embed=em)


    #play next song 
    def play_next(self, svr_id):

        #if there are songs queued in music_queue
        if len(self.music_queue[svr_id]) > 0:

            #set is_playing to true if it is false
            if self.is_playing[svr_id] == False:
                self.is_playing[svr_id] = True

            #try to get the audio url of the first song in music_queue 
            id = self.music_queue[svr_id][0]["id"]
            utube_url = "https://www.youtube.com/watch?v=" + id
            url_req = get_audio_url(utube_url)

            #if getting the url is successful
            if url_req["success"] == True:
                m_url = url_req["source"]
                
                #remove the first element in music_queue
                self.current_song[svr_id] = self.music_queue[svr_id][0]
                self.music_queue[svr_id].pop(0)

                #play the audio from url in discord voice client
                self.vclient[svr_id].play(discord.FFmpegPCMAudio(m_url,**self.FFMPEG_OPTIONS), after=lambda e: self.play_next(svr_id=svr_id))
            
            #if getting the url is not successful
            elif url_req["success"] == False:
                
                #send message to discord channel saying that download has failed, playing next song
                title = self.music_queue[svr_id][0]["title"]
                coro = self.text_channel[svr_id].send('Could not download **{}**, playing next song!'.format(title))
                fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                try:
                    fut.result()
                except:
                    print("An error happened sending the message")

                #remove failed download song from music queue and play next song 
                self.music_queue[svr_id].pop(0)
                self.play_next(svr_id)

        #if there are no songs in music queue
        else:

            #set is_playing to false and current_song to None
            self.is_playing[svr_id] = False
            self.current_song[svr_id] = None


    #
    async def play_music(self, svr_id):
        if len(self.music_queue[svr_id]) > 0:
            if self.is_playing[svr_id] == False:
                self.is_playing[svr_id] = True

            #get the first url
            id = self.music_queue[svr_id][0]["id"]
            utube_url = "https://www.youtube.com/watch?v=" + id
            url_req = get_audio_url(utube_url)

            #if getting the url is successful
            if url_req["success"] == True:
                m_url = url_req["source"]
                    
                #remove the first element as you are currently playing it
                self.current_song[svr_id] = self.music_queue[svr_id][0]
                self.music_queue[svr_id].pop(0)

                self.vclient[svr_id].play(discord.FFmpegPCMAudio(m_url,**self.FFMPEG_OPTIONS), after=lambda e: self.play_next(svr_id=svr_id))
                self.is_playing[svr_id] == True

            #if getting the url is not successful
            elif url_req["success"] == False:
                title = self.music_queue[svr_id][0]["title"]
                await self.text_channel[svr_id].send('Could not download **{}**, playing next song!'.format(title))
                self.music_queue[svr_id].pop(0)
                self.play_next(svr_id)
        else:
            self.is_playing[svr_id] = False
            self.current_song[svr_id] = None

#---------------------------------------------------------------------------
#--------------------------------listeners----------------------------------
#---------------------------------------------------------------------------

    #executes on command errors
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        print(error)
        await self.show_help(ctx, ttl="Command error, these are the available commands:")

    
    #executes on reaction add
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):

        #initiate svr details in data structures if not initiated yet 
        svr_id = reaction.message.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id)

        #handles what to do when previous or next page reaction is clicked on queue message
        if svr_id in self.queue_msg: 
            if reaction.message.id == self.queue_msg[svr_id]["msg"].id:
                if user != self.bot.user:
                    if str(reaction.emoji) == "⏮️":
                        await reaction.remove(user)
                        await self.flip_page(svr_id, 0)
                    elif str(reaction.emoji) == "⏭️":
                        await reaction.remove(user)
                        await self.flip_page(svr_id, 1)

#---------------------------------------------------------------------------
#---------------------------------commands----------------------------------
#---------------------------------------------------------------------------

    #show help message when h command is called
    @commands.command(name = 'h', help = "help command", aliases = ["help"])
    async def help(self, ctx):
        await self.show_help(ctx)

    #adds song to queue when p command is called
    @commands.command(name="p", help="play song", aliases = ["play"])
    async def play(self, ctx, *args):
        svr_id = ctx.author.guild.id
        author_vc = ctx.author.voice.channel
        
        #initiate svr details in data structures if not initiated yet 
        if svr_id not in self.music_queue:
            self.reset(svr_id)

        self.text_channel[svr_id] = ctx

        #if author is not connected to a voice channel, tell user to connect to a voice channel
        if author_vc == None: 
            await ctx.send("**Connect to a voice channel!")

        #if bot is currently playing in another channel, tell user that bot is currently playing in another channel
        elif (author_vc != self.voice_channel[svr_id]) and (self.is_playing[svr_id] == True): 
            await ctx.send("**Currently playing in another channel.**")

        #add music to queue and start playing in all other cases 
        else:
            
            self.voice_channel[svr_id] = author_vc
            query = " ".join(args)

            #if query is a youtube playlist link
            if "playlist?list" in query: 

                #get the id and title of all videos in playlist and add to music_queue
                playlist_id = get_id(query)
                songs = get_playlist_details(playlist_id=playlist_id)
                self.music_queue[svr_id].extend(songs)
                nb_of_songs = len(songs)
                await ctx.send("**{}** songs added to queue!".format(nb_of_songs))

                #connect to voice channel if not connected yet
                if self.is_playing[svr_id] != True:

                    #try to connect to voice channel if bot not already connected
                    if self.vclient[svr_id] == None:
                        self.vclient[svr_id] = await self.voice_channel[svr_id].connect()

                    #move to voice channel where the author is
                    else:
                        await self.vclient[svr_id].move_to(self.voice_channel[svr_id])

                    #start playing music
                    await self.play_music(svr_id)
                    return None
                
            #if query is a video link
            elif "watch?v=" in query:

                id = get_id(query)
                song = get_video_details_id(id)
                self.music_queue[svr_id].append(song)

                title = song["title"]
                await ctx.send("**{}** added to queue!".format(title))

                if self.is_playing[svr_id] != True:
                    #try to connect to voice channel if you are not already connected
                    if self.vclient[svr_id] == None:
                        self.vclient[svr_id] = await self.voice_channel[svr_id].connect()
                    else:
                        await self.vclient[svr_id].move_to(self.voice_channel[svr_id])


                    await self.play_music(svr_id)
                    return None

            else:
                song = get_video_details(query)
                self.music_queue[svr_id].append(song)
                
                title = song["title"]
                await ctx.send("**{}** added to queue!".format(title))

                if self.is_playing[svr_id] != True:
                    #try to connect to voice channel if you are not already connected
                    if self.vclient[svr_id] == None:
                        self.vclient[svr_id] = await self.voice_channel[svr_id].connect()
                    else:
                        await self.vclient[svr_id].move_to(self.voice_channel[svr_id])


                    await self.play_music(svr_id)
                    return None


    @commands.command(name="q", help="Displays the current songs in queue", aliases = ["queue"])
    async def show_queue(self, ctx):
        svr_id = ctx.author.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id=svr_id)
        self.text_channel[svr_id] = ctx
        em = discord.Embed()
        nb_songs = len(self.music_queue[svr_id])
        if nb_songs == 0:
            if self.current_song[svr_id] == None:
                await ctx.send("**No music in queue**")
                return None
            else:
                title = self.current_song[svr_id]["title"]
                id = self.current_song[svr_id]["id"]
                em.add_field(name="Currently playing", value="[**{0}**](https://www.youtube.com/watch?v={1})\n".format(title, id), inline=False)
                
                name = "Coming up next:"
                val = "None"
                em.add_field(name=name, value=val, inline=False)
                
        elif nb_songs <= self.SONGS_PER_PAGE:
            title = self.current_song[svr_id]["title"]
            id = self.current_song[svr_id]["id"]
            em.add_field(name="Currently playing", value="[**{0}**](https://www.youtube.com/watch?v={1})\n".format(title, id), inline=False)
            
            name = "Coming up next:"
            val = ""

            for i in range(nb_songs):
                title = self.music_queue[svr_id][i]["title"]
                id = self.music_queue[svr_id][i]["id"]
                val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)

            em.add_field(name=name, value = val, inline = False)
        elif nb_songs > self.SONGS_PER_PAGE:
            title = self.current_song[svr_id]["title"]
            id = self.current_song[svr_id]["id"]
            em.add_field(name="Currently playing", value="[**{0}**](https://www.youtube.com/watch?v={1})\n".format(title, id), inline=False)
            
            name = "Coming up next:"
            val = ""

            for i in range(self.SONGS_PER_PAGE):
                title = self.music_queue[svr_id][i]["title"]
                id = self.music_queue[svr_id][i]["id"]
                val += " {0}. [**{1}**](https://www.youtube.com/watch?v={2})\n\n".format(i+1, title, id)

            em.add_field(name=name, value = val, inline = False)
            msg = await ctx.send(embed = em)
            self.queue_msg[svr_id] = {
                "msg" : msg,
                "prev_last" : self.SONGS_PER_PAGE
            }
            await asyncio.gather(
                msg.add_reaction("⏮️"),
                msg.add_reaction("⏭️")
            )
            return None

        await ctx.send(embed = em)        


    @commands.command(name="s", help="Skips the current song being played", aliases = ["skip"])
    async def skip(self, ctx):
        svr_id = ctx.author.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id=svr_id)

        if self.vclient[svr_id] != None:
            self.vclient[svr_id].stop()
            await ctx.send("**{}** skipped!".format(self.current_song[svr_id]["title"]))
        else:
            await ctx.send("**No music playing**")


    @commands.command(name="rm", help="remove specific song from queue", aliases = ["remove"])
    async def remove(self, ctx, arg):
        svr_id = ctx.author.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id=svr_id)
        
        try:
            index = int(arg) - 1
        except:
            await ctx.send("Invalid argument, **<index>** in **{}rm <index>** must be a number.".format(self.pref))
        else:
            queue_len = len(self.music_queue[svr_id])
            if index < queue_len and index >= 0:
                song = self.music_queue[svr_id][index]
                title = song["title"]
                self.music_queue[svr_id].pop(index)
                await ctx.send("**{}** removed from queue!".format(title))
            else:
                await ctx.send("No song in position {}.".format(index + 1))
        

    @commands.command(name="clr", help="Clear music queue", aliases = ["clear"])
    async def clear_queue(self, ctx):
        svr_id = ctx.author.guild.id
        if svr_id in self.music_queue:
            if len(self.music_queue[svr_id]) > 0:
                self.is_playing[svr_id] = False
                self.current_song[svr_id] = None
                self.music_queue[svr_id] = []
                self.vclient[svr_id].stop()
                await ctx.send("**Music queue cleared**")
                return None

        await ctx.send("**Nothing to clear**")


    @commands.command(name="m", help = "move song from certain index to certain index", aliases = ['move'])
    async def move_song(self, ctx, *args):
        svr_id = ctx.author.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id=svr_id)
        
        queue_len = len(self.music_queue[svr_id])       
        try:
            song_index = int(args[0]) - 1
            target_index = int(args[1]) -1
        except:
            await ctx.send("Invalid arguments, **<song index>** and **<target index>** in **{}m <song index> <target index>** must be numbers".format(self.pref))
        else:
            if (queue_len > song_index) and (queue_len > target_index):
                if song_index != target_index:
                    song = self.music_queue[svr_id][song_index]
                    self.music_queue[svr_id].pop(song_index)
                    self.music_queue[svr_id].insert(target_index, song)
                    await ctx.send("**{}** moved to position {}.".format(song['title'], target_index+1))
                else:
                    await ctx.send("Invalid arguments, **<song index>** and **<target index>** in **{}m <song index> <target index>** can not be the same".format(self.pref))
            else:
                await ctx.send("Index out of range, please ensure that **<song index>** and **<target index>** is less than queue length.")


    @commands.command(name="sf", help="Shuffles music queue", aliases = ["shuffle", "shuf"])
    async def shuffle_queue(self, ctx):
        svr_id = ctx.author.guild.id
        if svr_id not in self.music_queue:
            self.reset(svr_id=svr_id)

        random.shuffle(self.music_queue[svr_id])
        await ctx.send("**Queue shuffled!**")


    @commands.command(name="d", help="Disconnects bot from channel", aliases = ["dc", "disconnect"])
    async def leave(self, ctx):
        svr_id = ctx.author.guild.id
        await asyncio.gather(
            self.vclient[svr_id].disconnect(),
            ctx.send("**Disconnected**")
        )
        self.reset(svr_id)


