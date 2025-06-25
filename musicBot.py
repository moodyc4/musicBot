#!/opt/discord/musicBot/bin/python3
import discord
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
from yt_dlp import YoutubeDL
import asyncio
import re

TOKEN = open("secret", "r").read()
intents=discord.Intents.default()
intents.message_content = True
client = commands.Bot(intents=intents, command_prefix = '\'')

ydl_opts = {
    'format': 'ogg/webm/bestaudio/best',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'client': 'tv',
}

ffmpeg_opts = {
    'options': '-vn'
}

q = []
requests = []
status = "Project Zomboid"
ytdl = YoutubeDL(ydl_opts)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        with ytdl:
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            
        return cls(discord.FFmpegPCMAudio(url, **ffmpeg_opts), data=data)

def is_connected(ctx):
    voice_client = ctx.message.guild.voice_client
    return voice_client and voice_client.is_connected()

async def setStatus():
    await client.change_presence(activity=discord.Game(status))

@client.event
async def on_ready():
    await setStatus()
    print('Music Bot Online.')

@client.command(aliases=['p', 'a', 'add'], help="Start the queue or add a song to the queue and play immediately")
async def play(ctx, *, request=""):
    server = ctx.message.guild
    voice_channel = server.voice_client
    # Join voice channel if necessary
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    else:
        try:
            channel = ctx.message.author.voice.channel
            await channel.connect()
        except: 
            pass
    
    if request:
        await ctx.send("**Processing...**")

        # Get data from ytdl
        with ytdl:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(request, download=False))

        # If request has a playlist header
        if 'entries' in data:
            for video in data["entries"]:
                if not video:
                    print("ERROR: Unable to get info. Continuing...")
                    await ctx.send("Can't play this video...  *Is it age restricted?*")
                    continue
                newReq = []
                for prop in ['url', 'fulltitle', 'uploader_id', 'original_url']:
                    newReq.append(str(video.get(prop)))
                await ctx.send('> *Adding* `{0}` [{1}]({2}) *to queue*'.format(newReq[2], newReq[1], newReq[3]))
                q.append(newReq)
        # If request is not a playlist (or no playlist header)
        else:
            newReq = [
                data.get('url'),
                data.get('fulltitle'),
                data.get('uploader_id'),
                data.get('original_url')
            ]
            await ctx.send('> *Adding* `{0}` [{1}]({2}) *to queue*'.format(newReq[2], newReq[1], newReq[3]))
            q.append(newReq)
    elif not request:
        if len(q) == 0:
            await ctx.send('The queue is empty.')
        else:
            pass
    # While queue is not empty, pass url to ydl and play
    while q:
        try:
            while voice_channel.is_playing() or voice_channel.is_paused():
                await asyncio.sleep(2)
                pass
        except AttributeError:
            pass
        # Try to play the video
        url = str(q[0][0])
        video_link = str(q[0][3])
        title = str(q[0][1])
        author = str(q[0][2])
        try:
            vc = ctx.voice_client
            source = await YTDLSource.from_url(url, loop=client.loop)
            vc.play(source)
            await ctx.send('**Now Playing:** `{0}` [{1}]({2})'.format(author, title, video_link))
        except:
            print('Huh?')
            break
        
        del(q[0])

@client.command(aliases=['j'])
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send('You are not in a voice channel!')
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@client.command()
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    await voice_client.disconnect()

@client.command(aliases=['s', 'sk'])
async def skip(ctx):
    global q
    server = ctx.message.guild
    voice_channel = server.voice_client
    if len(q) > 0:
        voice_channel.stop()
    else:
        await ctx.send("Your queue is empty!")
        return
    await ctx.send("*Skipped*")
    await play(ctx)

@client.command()
async def pause(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    if voice_channel:
        voice_channel.pause()
    else:
        await ctx.send("There is nothing to pause!")

@client.command()
async def resume(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    if voice_channel:
        voice_channel.resume()
    else:
        await ctx.send("Nothing is paused, looking for the play command?")

@client.command()
async def stop(ctx):
    server = ctx.message.guild
    voice_channel = server.voice_client
    if voice_channel:
        voice_channel.stop()
    else:
        await ctx.send("Nothing is playing!")

@client.command(aliases=['q'], help='View the current queue')
async def queue(ctx):
    global q
    if not q==[]:
        ph = []
        for item in q:
            title = item[1]
            author = item[2]
            video_link = item[3]
            ph.append('`{0}` [{1}]({2})'.format(author, title, video_link))
        await ctx.send(f'> **Current queue:** {ph}')
    else:
        await ctx.send("The queue is empty!")

@client.command(aliases=['r', 'rm'], help='Will remove the specified song from the queue')
async def remove(ctx, number):
    global q
    i = int(number) - int(1)
    try:
        del(q[int(i)])
        if not q==[]:
            await ctx.send(f'Queue is now: `{q}`')
        else:
            await ctx.send(f'Queue is now empty')
    except:
        await ctx.send("Either your queue is empty or index is out of range")

client.run(TOKEN)
