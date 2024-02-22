#!/usr/bin/python3
import discord
from discord.ext import commands, tasks
from discord.voice_client import VoiceClient
import yt_dlp
import asyncio
import re

TOKEN = open("secret", "r").read()
intents=discord.Intents.default()
intents.message_content = True
client = commands.Bot(intents=intents, command_prefix = '\'')

ytdl_format_options = {
    'format': 'bestaudio/best',
    #'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    #'restrictfilenames': True,
    #'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    #'extract_flat': 'in_playlist',
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

global q
q = []
status = "Palworld"
# YTDL Object
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        global q
        try:
            with ytdl:
                loop = loop or asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                
                realURL = data.get('url')
        except:
            print('This nigga shat himself')
        
        if 'entries' in data:
            # add playlist to queue
            no = 0
            vid = data['entries']
            for i, item in enumerate(vid):
                vid = data['entries'][i]
                if (no > 0):
                    q.append(vid['original_url'])
                else:
                    realURL = vid['url']
                no = no + 1
            
        return cls(discord.FFmpegPCMAudio(realURL, **ffmpeg_options), data=data)

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
async def play(ctx, *, url=""):
    global q
    server = ctx.message.guild
    voice_channel = server.voice_client
    # Join voice channel
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return
    else:
        try:
            channel = ctx.message.author.voice.channel
            await channel.connect()
        except: 
            pass
    # Take url, fix short link if necessary + add to queue
    if url:
        newURL = ""
        isShort = re.search(r'shorts', url)
        if(isShort):
            newURL = url.replace('/shorts/', '/watch?v=')
            url = newURL
        q.append(url)
        await ctx.send(f'`{url}` added to the queue')
    elif not url:
        if len(q) == 0:
            await ctx.send('The queue is empty.')
        else:
            pass
    # While queue is not empty, pass url to ytdl and play
    while q:
        try:
            while voice_channel.is_playing() or voice_channel.is_paused():
                await asyncio.sleep(2)
                pass
        except AttributeError:
            pass
        try:
            vc = ctx.voice_client
            #print(client.loop)
            source = await YTDLSource.from_url(q[0], loop=client.loop)
            vc.play(source)
            #play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        except:
            print('Player shat itself')
            break
        del(q[0])
        await ctx.send('**Now Playing:** {}'.format(source.title))

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
        await ctx.send(f'Current queue: `{q}`')
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
