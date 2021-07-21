
import tokenkeycode
import discord
from discord.ext import tasks

# 接続に必要なオブジェクトを生成
intents = discord.Intents.default()  # デフォルトのIntentsオブジェクトを生成
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    # 起動したらターミナルにログイン通知が表示される
    print('ログインしました')
    print('client.guilds: %d' % len(client.guilds))

    for g in client.guilds:
        await g.leave()


client.run(tokenkeycode.TOKEN)
