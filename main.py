import os
import base64
import mimetypes
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
PERSON_NAME      = os.getenv("PERSON_NAME", "the student")

SYSTEM_PROMPT = (
    "You are a knowledgeable and patient economics tutor. The student is an Undergraduate Economics student. "
    "You help this student understand micro and macroeconomics concepts, work through problem sets, interpret graphs, and review homework. "
    "When answering, clearly explain your reasoning step by step. Be open to their way of doing the question and always encourage them. Be short and to the point."
    "Use real-world examples where helpful. "
    "Politely redirect any off-topic questions back to economics. Use Toronto slang when the content is not related to economics. "
    f"The person using this bot is named {PERSON_NAME}. "
    "No use of em-dashes or other special characters. Try to be as concise as possible."
    "No use of emojis. Do not focus on the student's grammar or spelling. Just focus on the content."
    "No use of markdown. Just use plain text."
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

    user_text = (message.content or "").strip()

    image_blocks = []
    for attachment in message.attachments:
        content_type = attachment.content_type
        if not content_type:
            content_type = mimetypes.guess_type(attachment.filename or "")[0]
        if not content_type or not content_type.startswith("image/"):
            continue

        data = await attachment.read()
        b64 = base64.b64encode(data).decode("utf-8")
        image_blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": content_type or "image/png",
                    "data": b64,
                },
            }
        )

    if image_blocks:
        user_content = image_blocks[:]
        if user_text:
            user_content.append({"type": "text", "text": user_text})
        else:
            user_content.append({"type": "text", "text": "Describe the image."})
    else:
        user_content = user_text

    try:
        response = claude.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=message_history[channel_id] + [{"role": "user", "content": user_content}],
        )
        answer = response.content[0].text
        if user_text:
            stored_user = user_text
        elif image_blocks:
            stored_user = "[image]"
        else:
            stored_user = ""

        message_history[channel_id].append({"role": "user", "content": stored_user})
        message_history[channel_id].append({"role": "assistant", "content": answer})
        message_history[channel_id] = message_history[channel_id][-MAX_HISTORY:]
        for chunk in [answer[i:i+2000] for i in range(0, len(answer), 2000)]:
            await message.channel.send(chunk)
    except Exception as e:
        print(f"claude error: {e}")
        await message.channel.send("there was an error processing your message.")
   
client.run(DISCORD_TOKEN)
