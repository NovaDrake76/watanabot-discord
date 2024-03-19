import json
import nextcord
from nextcord.ext import commands
from quart import Quart, request, jsonify
import aiohttp
import asyncio
import os

# Discord bot setup
intents = nextcord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Flask app setup, using Quart for asyncio compatibility
app = Quart(__name__)

# Async HTTP session for making requests within async functions
async def get_async_session():
    return aiohttp.ClientSession()

# Load or initialize subscriptions
def load_subscriptions():
    try:
        with open('subscriptions.json', 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}  # Return an empty dict if JSON is invalid
    except FileNotFoundError:
        return {}  # Return an empty dict if file does not exist

# Save subscriptions to a file
def save_subscriptions(subscriptions):
    with open('subscriptions.json', 'w') as file:
        json.dump(subscriptions, file)

subscriptions = load_subscriptions()

@bot.command(name='subscribe')
async def subscribe(ctx):
    """Subscribes the current channel to receive posts."""
    channel_id = str(ctx.channel.id)
    subscriptions[channel_id] = ctx.channel.name
    save_subscriptions(subscriptions)
    await ctx.send(f"Subscribed {ctx.channel.name} to receive posts.")

@bot.command(name='unsubscribe')
async def unsubscribe(ctx):
    """Unsubscribes the current channel from receiving posts."""
    channel_id = str(ctx.channel.id)
    if channel_id in subscriptions:
        del subscriptions[channel_id]
        save_subscriptions(subscriptions)
        await ctx.send(f"Unsubscribed {ctx.channel.name} from receiving posts.")
    else:
        await ctx.send("This channel is not subscribed.")

async def post_image_to_subscribed_channels(s3_url, text):
    """Posts the image to all subscribed channels."""
    async_session = await get_async_session()
    for channel_id in subscriptions:
        channel = bot.get_channel(int(channel_id))
        if channel:
            async with async_session.get(s3_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    await channel.send(content=text, file=nextcord.File(fp=data, filename="image.png"))

@app.route('/notify', methods=['POST'])
async def notify():
    """Receives notifications and triggers posting to subscribed channels."""
    data = await request.json
    s3_url = data.get('s3_url')
    text = data.get('text')
    asyncio.create_task(post_image_to_subscribed_channels(s3_url, text))
    return jsonify({"message": "Notification received"}), 200

async def run_bot():
    await bot.start(os.getenv('DISCORD_TOKEN'))

@app.before_serving
async def startup():
    asyncio.create_task(run_bot())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
