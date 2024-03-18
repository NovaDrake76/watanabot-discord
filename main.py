import json
import nextcord
from nextcord.ext import commands, tasks
from flask import Flask, request, jsonify
import requests
from threading import Thread
import os

# Discord bot setup
intents = nextcord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Flask app setup
app = Flask(__name__)

# Load or initialize subscriptions
def load_subscriptions():
    try:
        with open('subscriptions.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

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
    for channel_id in subscriptions:
        channel = bot.get_channel(int(channel_id))
        if channel:
            await channel.send(content=text, file=nextcord.File(fp=requests.get(s3_url, stream=True).raw, filename="image.png"))

@app.route('/notify', methods=['POST'])
def notify():
    """Receives notifications and triggers posting to subscribed channels."""
    data = request.json
    s3_url = data.get('s3_url')
    text = data.get('text')
    bot.loop.create_task(post_image_to_subscribed_channels(s3_url, text))
    return jsonify({"message": "Notification received"}), 200

def run_bot():
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    # Run the bot in a separate thread
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, use_reloader=False)
