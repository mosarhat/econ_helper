import os
import discord
import anthropic

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

ALLOWED_CHANNELS = {"econ-homework"}
MODEL            = "claude-opus-4-5"
MAX_HISTORY      = 20

SYSTEM_PROMPT = (
    "You are a knowledgeable and patient economics tutor. The student is an Undergraduate Economics student. "
    "You help students understand micro and macroeconomics concepts, work through problem sets, interpret graphs, and review homework. "
    "When answering, clearly explain your reasoning step by step. Be open to their way of doing the question and always encourage them. "
    "Use real-world examples where helpful. Be simple, but to the point. "
    "Politely redirect any off-topic questions back to economics."
)

message_history: dict[int, list] = {}

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.name not in ALLOWED_CHANNELS:
        return

    channel_id = message.channel.id
    if channel_id not in message_history:
        message_history[channel_id] = []

    message_history[channel_id].append({"role": "user", "content": message.content})
    message_history[channel_id] = message_history[channel_id][-MAX_HISTORY:]

    try:
        response = claude.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=message_history[channel_id],
        )
        answer = response.content[0].text
        message_history[channel_id].append({"role": "assistant", "content": answer})
        print(message_history)
        for chunk in [answer[i:i+2000] for i in range(0, len(answer), 2000)]:
            await message.channel.send(chunk)
    except Exception as e:
        print(f"claude error: {e}")
        await message.channel.send("there was an error processing your message.")
   
client.run(DISCORD_TOKEN)
