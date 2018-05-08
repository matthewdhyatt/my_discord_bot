# https://github.com/Rapptz/discord.py/blob/async/examples/reply.py
import discord
import os

#token=os.environ['TOKEN']
#os.environ.get('TOKEN')

client = discord.Client('NDQyODEyMTI5ODcyMDUyMjI1.DdHsIQ.xZAZaPRYvIpJh-wOCuo1CgkvJU8')

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await client.send_message(message.channel, msg)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('NDQyODEyMTI5ODcyMDUyMjI1.DdHsIQ.xZAZaPRYvIpJh-wOCuo1CgkvJU8')
