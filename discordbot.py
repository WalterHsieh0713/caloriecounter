import discord
from discord.ext import commands
import base64
import json
import os
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()
discord_bot_token = os.getenv("DISCORD_BOT_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Define the intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize OpenAI client
client = OpenAI(api_key = openai_api_key)

class MealInfo(BaseModel):
    meal_name: str
    calories: int
    protein: int
    carbs: int
    fat: int

# Initialize SQLite database
def initialize_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            dietary_preferences TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER NOT NULL,
            fat INTEGER NOT NULL,
            carbs INTEGER NOT NULL,
            UNIQUE(name)
        )
    ''')
    c.execute('''
            CREATE TABLE IF NOT EXISTS user_meal_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                meal_id INTEGER NOT NULL,
                meal_date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES user_info(user_id),
                FOREIGN KEY (meal_id) REFERENCES meals(id)
            )
        ''')

    conn.commit()
    conn.close()

# Save user information
def save_user_info(user_id, username, dietary_preferences=None):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()

    # Check if the user already exists
    c.execute('''
        SELECT * FROM user_info WHERE user_id = ?
    ''', (user_id,))
    user = c.fetchone()

    # If the user doesn't exist, insert their info
    if not user:
        c.execute('''
            INSERT INTO user_info (user_id, username, dietary_preferences)
            VALUES (?, ?, ?)
        ''', (user_id, username, dietary_preferences))
    # If user exists, update their username and dietary preferences
    else:
        c.execute('''
            UPDATE user_info
            SET username = ?, dietary_preferences = ?
            WHERE user_id = ?
        ''', (username, dietary_preferences, user_id))

    conn.commit()
    conn.close()

# Save user data and meal information to the database
def save_user_data(user_id, username, response_json):
    # Save user info
    save_user_info(user_id, username)

    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    print("response", response_json)
    # Save meal data and link to the user
    c.execute('''
        INSERT INTO meals (name, calories, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            calories=excluded.calories,
            protein=excluded.protein,
            fat=excluded.fat,
            carbs=excluded.carbs
    ''', (response_json['meal_name'], response_json['calories'], response_json['carbs'], response_json['protein'], response_json['fat']))

    meal_id = c.lastrowid if c.lastrowid != 0 else c.execute('SELECT id FROM meals WHERE name = ?', (response_json['meal_name'],)).fetchone()[0]

    c.execute('''
        INSERT INTO user_meal_history (user_id, meal_id, meal_date)
        VALUES (?, ?, DATE('now'))
    ''', (user_id, meal_id))

    conn.commit()
    conn.close()
    

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

def openai_vision(img_path: str) -> dict:
    client = OpenAI(api_key=openai_api_key)
    
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "system",
                "content": """You are a helpful nutritionist who gives me helpful advice and tells me the calories, fat, and protein of each meal"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_base64_url(img_path)
                        },
                    },
                ],
            }
        ],
        response_format=MealInfo,
        temperature=1,
        max_tokens=256,
    )

    # Load the JSON response from OpenAI's API
    response_json = json.loads(response.choices[0].message.content)

    return response_json

def generate_weekly_meal_plan(user_id):
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''
        SELECT m.name, m.calories, m.protein, m.fat, m.carbs
        FROM meals m
        JOIN user_meal_history h ON m.id = h.meal_id
        WHERE h.user_id = ?
        ORDER BY h.meal_date DESC
        LIMIT 7
    ''', (user_id,))
    recent_meals = c.fetchall()
    suggestions = []

    if not recent_meals:
        conn.close()
        return None

    for i in range(7):
        suggestions.append(recent_meals[i % len(recent_meals)])
    
    conn.close()
    return suggestions

@bot.command(name='weekly_plan')
async def weekly_plan(ctx):
    user_id = str(ctx.author.id)
    username = ctx.author.name
    
    suggestions = generate_weekly_meal_plan(user_id)
    
    if not suggestions:
        await ctx.send(f"Sorry {username}, I don't have enough data to generate a meal plan for you yet.")
        return
    
    response_text = f"Here is your meal plan for the next week, {username}:\n\n"
    for i, (meal_name, calories, protein, fat, carbs) in enumerate(suggestions):
        response_text += f"Day {i+1}: {meal_name} - {calories} calories, {protein}g protein, {fat}g fat, {carbs}g carbs\n"
    
    await ctx.send(response_text)

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

                user_id = str(message.author.id)
                username = message.author.name

                response_json = openai_vision(image_path)

                save_user_data(user_id, username, response_json)

                await message.channel.send(response_json)

    # Process commands if the message is a command
    await bot.process_commands(message)

initialize_db()

bot.run(discord_bot_token)
