import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from flask import Flask
from threading import Thread
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# ------------------- ENV VARIABLES -------------------
TOKEN = os.environ["TOKEN"]
FLEX_CHANNEL_ID = int(os.environ.get("FLEX_CHANNEL_ID", 1356627399004913846))

# ------------------- DISCORD BOT SETUP -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)
client_tree = bot.tree

REACTION_TRIGGERS = ["💪", "🔥", "😎"]
posts_triggered = set()

# ------------------- FLASK KEEP-ALIVE -------------------
app = Flask('')

@app.route('/')
def home():
    return "Oracle Koala is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# ------------------- HUGGING FACE AI SETUP (CPU-Friendly, small model) -------------------
tokenizer = AutoTokenizer.from_pretrained(
    "TheBloke/vicuna-1.1-1B-HF",
    cache_dir="/tmp"
)
model = AutoModelForCausalLM.from_pretrained(
    "TheBloke/vicuna-1.1-1B-HF",
    cache_dir="/tmp",
    torch_dtype=torch.float32,
    device_map="auto"
)

def get_oracle_response(user_question):
    personality_prompt = (
        "You are Oracle Koala, a wise but cheeky Australian koala. "
        "Answer clearly but sprinkle in Aussie slang, eucalyptus/gumtree references, "
        "and playful humor. Some responses should be short and snappy, some can be detailed.\n\n"
        f"User: {user_question}\nKoala:"
    )
    try:
        inputs = tokenizer(personality_prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=80,
                do_sample=True,
                temperature=0.7,
                top_p=0.9
            )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response.replace(personality_prompt, "").strip()
        return response
    except Exception as e:
        print(f"Hugging Face error: {e}")
        fallback_responses = [
            "Oi mate, ask me something else! 🐨",
            "The oracle is pondering… try again 🌿",
            "G’day, give me a proper question! 🔥🐨"
        ]
        return random.choice(fallback_responses)

# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await client_tree.sync()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == FLEX_CHANNEL_ID and message.attachments:
        try:
            await message.add_reaction("🐨")
            await message.add_reaction("🔥")
            if random.random() < 0.5:
                comment_options = [
                    "Now that’s proper fire, mate 🔥🐨",
                    "Flex certified by the Oracle 🌿",
                    "Looks like a drop bear wouldn’t stand a chance 💪🐨"
                ]
                await message.channel.send(random.choice(comment_options))
        except Exception as e:
            print(f"Flex channel reaction error: {e}")

    if bot.user in message.mentions:
        try:
            content = message.content.replace(f"<@{bot.user.id}>", "").strip()
            if content:
                response = get_oracle_response(content)
                await message.channel.send(response)
            else:
                await message.channel.send("G’day mate, what’s the question? 🐨")
        except Exception as e:
            print(f"Error in mention handling: {e}")
            await message.channel.send("Oi mate, something went wonky")

    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id == FLEX_CHANNEL_ID:
        return

    post_id = payload.message_id
    if post_id in posts_triggered:
        return

    if str(payload.emoji) in REACTION_TRIGGERS:
        if random.random() < 0.5:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(post_id)
            reply_options = [
                "Oi mate, I see ya flexin’ 💪🐨",
                "That’s fire, mate 🔥🐨",
                "Cool as a gumtree in the breeze 😎🌿",
                "The oracle approves, mate 🐨✨"
            ]
            await channel.send(random.choice(reply_options))
        posts_triggered.add(post_id)

# ------------------- SLASH COMMAND -------------------
@client_tree.command(name="koala", description="Ask Oracle Koala a question")
async def koala(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    answer = get_oracle_response(question)
    await interaction.followup.send(answer)

# ------------------- RUN BOT -------------------
bot.run(TOKEN)
