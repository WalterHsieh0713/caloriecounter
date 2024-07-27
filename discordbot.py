import discord
from discord.ext import commands
import base64
import json
import os
from openai import OpenAI

# Define the intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize OpenAI client
client = OpenAI(api_key="sk-proj-5bCTXqjWpQ9TzAuIpuawT3BlbkFJVO4VuuTckV3imEf077jh")

def image_to_base64_url(image_path):
    # Open the image file in binary mode
    with open(image_path, 'rb') as image_file:
        # Read the image file and encode it to base64
        base64_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # Get the MIME type of the image (e.g., 'image/png', 'image/jpeg')
    mime_type = f"image/{image_path.split('.')[-1]}"
    
    # Create the base64 URL
    base64_url = f"data:{mime_type};base64,{base64_string}"
    
    return base64_url

def openai_vision(img_path: str) -> str:
    client = OpenAI(
        api_key = "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"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": """You are a helpful nutritionist who gives me helpful advice and tells me calories, fat, and protein of each meal, giving me the information using JSON.
                Example response: {"egg fried rice": {"calories": 100, "fat": 100, "protein": 100, "carbs": 100}, "soup": {"calories": 100, "fat": 100, "protein": 100, "carbs": 100}}"""
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "image_url",
                "image_url": {
                    "url": image_to_base64_url(img_path)
                }
                }
            ]
            },
            
        ],
        temperature=1,
        max_tokens=256,
    )
   # print(response.choices[0].message.content)
    resp = json.loads(response.choices[0].message.content)
    # print(resp)
    result = ""
    for key, value in resp.items():
        result += f"{key} has:\n {value['calories']} calories\n {value['protein']} grams of protein\n {value['fat']} grams of fat\n {value['carbs']} grams of carbs."
    return result

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('Ready to receive images!')

@bot.event
async def on_message(message):
    # Avoid the bot responding to its own messages
    if message.author == bot.user:
        return

    # Check if the message contains attachments
    if message.attachments:
        for attachment in message.attachments:
            # Check if the attachment is an image
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                # Save the image to a local file
                image_path = os.path.join('received_images', attachment.filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                await attachment.save(image_path)
                print(f'Received and saved image: {attachment.filename}')

                await message.channel.send(openai_vision(image_path))

    # Process commands if the message is a command
    await bot.process_commands(message)

bot.run('MTI2NjU5MzM2NjA1Mzc1MjkxMw.G3o41L.WN7n4YxiFByd3Z1OT1RrrK-CzBcJRLS0Vlj0yY')
