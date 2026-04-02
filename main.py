import os
import base64
import mimetypes
from io import BytesIO
from PIL import Image
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
PERSON_NAME      = os.getenv("PERSON_NAME", "the student")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf"}
MAX_PDF_BYTES = 5 * 1024 * 1024

SYSTEM_PROMPT = (
    "You are a knowledgeable and patient economics tutor. The student is an Undergraduate Economics student. "
    "You help this student understand micro and macroeconomics concepts, work through problem sets, interpret graphs, and review homework. "
    "When answering, clearly explain your reasoning step by step. Be open to their way of doing the question and always encourage them. Be short and to the point."
    "Use real-world examples where helpful. "
    "Politely redirect any off-topic questions back to economics, unless its something funny. Use Toronto slang when the content is not related to economics. "
    f"The person using this bot is named {PERSON_NAME}. "
    "No use of em-dashes or other special characters. Try to be as concise as possible."
    "No use of emojis. Do not focus on the student's grammar or spelling. Just focus on the content."
    "No use of markdown. Just use plain text."
)

message_history: dict[int, list] = {}

def detect_image_mime(data: bytes) -> str | None:
    try:
        with Image.open(BytesIO(data)) as img:
            fmt = (img.format or "").upper()
    except Exception:
        return None

    mapping = {
        "JPEG": "image/jpeg",
        "JPG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "GIF": "image/gif",
    }
    return mapping.get(fmt)

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
    if user_text.lower() == "/clear":
        message_history[channel_id] = []
        await message.channel.send("context cleared.")
        return

    image_blocks = []
    document_blocks = []
    for attachment in message.attachments:
        data = await attachment.read()
        content_type = detect_image_mime(data)
        if not content_type:
            content_type = attachment.content_type
        if not content_type:
            content_type = mimetypes.guess_type(attachment.filename or "")[0]

        if content_type in ALLOWED_IMAGE_TYPES:
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
        elif content_type in ALLOWED_DOCUMENT_TYPES:
            if len(data) > MAX_PDF_BYTES:
                await message.channel.send("pdf too large. max size is 5 mb.")
                continue
            b64 = base64.b64encode(data).decode("utf-8")
            document_blocks.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": content_type or "application/pdf",
                        "data": b64,
                    },
                }
            )

    if image_blocks or document_blocks:
        user_content = document_blocks + image_blocks
        if user_text:
            user_content.append({"type": "text", "text": user_text})
        else:
            user_content.append({"type": "text", "text": "Describe the attachment."})
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
        message_history[channel_id].append({"role": "user", "content": user_content})
        message_history[channel_id].append({"role": "assistant", "content": answer})
        for chunk in [answer[i:i+2000] for i in range(0, len(answer), 2000)]:
            await message.channel.send(chunk)
    except Exception as e:
        print(f"claude error: {e}")
        await message.channel.send("there was an error processing your message.")
   
client.run(DISCORD_TOKEN)
