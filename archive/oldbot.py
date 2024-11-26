import discord
from discord.ext import commands
import socket
import threading
import asyncio
import os
from PIL import Image, ImageDraw, ImageFont
import openai
import re
from datetime import datetime
# Replace this with your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

posted_games_players_freebet = set()
posted_games_players_other = set()
# Set up the bot
# intents = discord.Intents.default()
# intents.typing = True
# intents.presences = True

import discord
from discord.ext import commands
from discord.ui import Button, View
import re

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True 
client = discord.Client(intents=intents) 
bot = commands.Bot(command_prefix='!', intents=intents)
# Define a dictionary to map emojis to role names or IDs
emoji_to_role = {
    "👍": "Fanduel",
    "🤡": "nit",
    "😎": "5%",
    "🤩": "Aces"
    # Add more mappings as needed
}
role_to_id = {
    "Fanduel": 1115732713438195773,
    "FreeBets": 1115904331879825438,
    "Barstool": 1116116559212056598,
    "Superbook":1116130466773344317,
    "Betmgm":1116130539024437291,
    "Wynnbet":1116130988909678682,
    "Draftkings":1116130988909678682,
    "Williamhill_us":1116138362970058862,
    "Tipico_us":1116138843591168010,
    "Aces":1115734288114131055,
    "5%":1115735250539118703,
    "nit": 1115733528378875915
    # Add more mappings as needed
}
NOTIFSETUPMESSAGEID=1115723751523373197
sportschannels=[1115724819091177572,1115725809940959343,1115725994783944754]
import os
openai.api_key =  os.getenv('OPENAI_API_KEY')



@bot.command()
async def create_post(ctx):
    button=Button(label="Fanduel",style=discord.ButtonStyle.grey,emoji="🇫")
    view=View()
    view.add_item(button)
    await ctx.send("Bookmaker Notifications:",view=view)
system="""Given the following raw betting line: (input raw betting line), generate a series of engaging and informative tweets for expert sports bettors looking for quick bets. The tweet should not tag the bookmaker, should use gamblers humor, and should build a community around the account. The tweet should reflect the tone and personality of @MaybeEVBets - a little degen, a lot of strategy.

The tweet should prioritize the inclusion of:

    Player's name
    The betting condition (like 'Over 0.5 batter doubles', 'Under 1.5 Batter Hits')
    Current odds
    Fair value
    Expected Value (EV) in percentage format (note: input values are already in percentage terms, e.g., 0.12 is 0.1%, 1.58 is 1.58%)

If space allows, also include:

    The bookmaker's name (without tagging them)
    The commence time(note:given time is in UTC, must convert to EST first by subtracting 4 hours)

Every tweet should fit within the character limit of a standard tweet (280 characters).

Make sure it's formatted neatly for easy and quick reading!
"""


import openai
def gptCaption(tweet,model="gpt-4-0314",reply=2048):
    system_prompt=system
    
    response =openai.ChatCompletion.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system
            },
            {
                "role": "user",
                "content": tweet
            }
        ],
        max_tokens=reply,
        n=1,
        stop=None,
        temperature=0
    )
    return (response['choices'][0]['message']['content'])



async def gptCaption_async(tweet, model="gpt-4-0314", reply=2048):
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, gptCaption, tweet, model, reply)
    return response


caption_semaphore = asyncio.BoundedSemaphore(5)



async def generate_and_send_caption(message, thread):
    async with caption_semaphore:
        try:
            print(f"Generating caption for thread: {thread.name}")  # Add this log statement
            caption = await gptCaption_async(message)
            print(f"Caption generated for thread: {thread.name}")  # Add this log statement

            await thread.send(caption)
            print(f"Caption sent to thread: {thread.name}")  # Add this log statement
        except Exception as e:
            print(f"An error occurred while generating and sending the caption for thread {thread.name}: {e}")


async def assign_role_by_reaction(payload, add_role=True):
    guild = await bot.fetch_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)
    emoji = str(payload.emoji)
    if emoji in emoji_to_role:
        role_name = emoji_to_role[emoji]
        role = discord.utils.get(guild.roles, name=role_name)

        if role is not None:
            if add_role:
                await member.add_roles(role)
            else:
                await member.remove_roles(role)
        else:
            print(f"Role not found: {role_name}")
    else:
        print(f"Emoji not mapped to a role: {emoji}")

def text_to_image(text, width=900, height=1400, font_size=32):
    image = Image.new("RGB", (width, height), (221,235, 247))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Word wrap the text
    lines = []
    for original_line in text.splitlines():
        words = original_line.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            temp_line = line + " " + word
            if draw.textlength(temp_line, font) < width - 40:
                line = temp_line
            else:
                lines.append(line)
                line = word
        lines.append(line)

    # Draw the text
    y = 20
    for line in lines:
        draw.text((20, y), line, (0, 0, 0), font=font)
        y += font_size + 5

    return image


def watermark_image(image_path, watermark_text, output_path):
    # Open the original image
    original_image = Image.open(image_path).convert("RGBA")
    txt_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))

    # Load a font and set its size
    font = ImageFont.truetype("arial.ttf", 65)

    # Create an ImageDraw object
    draw = ImageDraw.Draw(txt_layer)

    # Calculate the size of the watermark text and create a transparent layer for it
    text_width, text_height = draw.textsize(watermark_text, font)
    watermark_layer = Image.new("RGBA", (text_width, text_height), (255, 255, 255, 0))

    # Draw the watermark text on the watermark layer
    draw_watermark = ImageDraw.Draw(watermark_layer)
    draw_watermark.text((0, 0), watermark_text, font=font, fill=(242, 242, 242, 242))

    # Rotate the watermark layer by 45 degrees and resize it to fit the image
    watermark_layer = watermark_layer.rotate(45, expand=1)
    ratio = min(original_image.width / watermark_layer.width, original_image.height / watermark_layer.height)
    watermark_layer = watermark_layer.resize((int(watermark_layer.width * ratio), int(watermark_layer.height * ratio)))

    # Calculate the position to place the watermark (center of the image)
    position = (int((original_image.width - watermark_layer.width) / 2), int((original_image.height - watermark_layer.height) / 2))

    # Paste the watermark layer onto the transparent text layer
    txt_layer.paste(watermark_layer, position, watermark_layer)

    # Combine the original image with the watermark layer
    watermarked_image = Image.alpha_composite(original_image, txt_layer)

    # Save the watermarked image
    watermarked_image.save(output_path)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == NOTIFSETUPMESSAGEID:
        await assign_role_by_reaction(payload, add_role=True)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == NOTIFSETUPMESSAGEID:
        await assign_role_by_reaction(payload, add_role=False)
# async def send_message_to_user(user_id, message, image_path=None):
#     try:
#         user = await bot.fetch_user(user_id)
#         if user is not None:
#             if image_path is not None:
#                 # Check if the file exists before attempting to send it
#                 if os.path.exists(image_path):
#                     file = discord.File(image_path)
#                     await user.send(message, file=file)
#                 else:
#                     print(f"File does not exist: {image_path}")
#                     await user.send(message)
#             else:
#                 await user.send(message)
#         else:
#             print(f"User not found: {user_id}")
#     except discord.HTTPException as e:
#         print(f"Failed to send message: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")



# async def send_message_to_channel(channel_id, message, image_path=None):
#     try:
#         channel = await bot.fetch_channel(channel_id)
#         if channel is not None:
#             if image_path is not None:
#                 if os.path.exists(image_path):
#                     file = discord.File(image_path)
#                     sent_message = await channel.send(message, file=file)
#                 else:
#                     print(f"File does not exist: {image_path}")
#                     sent_message = await channel.send(message)
#             else:
#                 sent_message = await channel.send(message)

#             # Create a thread for the sent message
#             thread_name = f"Thread for message {sent_message.id}"
#             await sent_message.create_thread(name=thread_name)
#         else:
#             print(f"Channel not found: {channel_id}")
#     except discord.HTTPException as e:
#         print(f"Failed to send message: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")

def get_sport(message):

    sport = None
    match = re.search(r"Sport:\s*(\w+)", message)
    if match:
        sport = match.group(1)
    return sport


def get_watermark_text(message):
    sport=get_sport(message)
    if sport is not None:
        # Generate the watermark text based on the sport
        watermark_text = f"MaybeEV-{sport}Bot"
    else:
        watermark_text = "MaybeEVBot"

    return watermark_text
image_counter=0
# async def generate_and_send_image(message,channel, image_path, watermark_text):
    
#     try:
#         # Generate the image and watermark it
#         print(f"Generating image: {image_path}")  # Add this print statement
#         if not watermark_text:
#             watermark_text=get_watermark_text(message)
#         image = text_to_image(message)
#         global image_counter
#         image_counter+=1
        
#         image.save(image_path)
       
#         watermark_image(image_path, watermark_text, image_path)

#         # Send the image to the channel
#         if os.path.exists(image_path):
#             file = discord.File(image_path)
#             await channel.send(file=file)
#         else:
#             print(f"File does not exist: {image_path}")
#     except Exception as e:
#         print(f"An error occurred while generating and sending the image: {e}")
async def generate_and_send_image(message, channel, image_path, watermark_text):
    global image_counter  # Add this line to access the global counter variable

    try:
        # Generate an image name using the counter
        unique_image_path = f"{image_path}_{image_counter}.png"
        image_counter += 1  # Increment the counter

        # Generate the image and watermark it
        print(f"Generating image: {unique_image_path}")  # Update this print statement
        if not watermark_text:
            watermark_text = get_watermark_text(message)
        image = text_to_image(message)

        image.save(unique_image_path)

        watermark_image(unique_image_path, watermark_text, unique_image_path)

        # Send the image to the channel
        if os.path.exists(unique_image_path):
            file = discord.File(unique_image_path)
            await channel.send(file=file)
        else:
            print(f"File does not exist: {unique_image_path}")
    except Exception as e:
        print(f"An error occurred while generating and sending the image: {e}")
# async def send_message_to_channel(channel_id, message, image_path=None, watermark_text=None):
#     try:
#         channel = await bot.fetch_channel(channel_id)
#         if channel is not None:
#             sent_message = await channel.send(message)

#             # Create a thread for the sent message
#             thread_name = f"Thread for message {sent_message.id}"
#             await sent_message.create_thread(name=thread_name)

#             # Generate and send the image asynchronously
#             if image_path is not None:
#                 print(f"Image path: {image_path}")  # Add this print statement
#                 asyncio.create_task(generate_and_send_image(message,channel, image_path, watermark_text))
#         else:
#             print(f"Channel not found: {channel_id}")
#     except discord.HTTPException as e:
#         print(f"Failed to send message: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")


def parse_message(message):
    elements = {}

    # Extract elements from the message using regular expressions
    sport_match = re.search(r"Sport:\s*(\w+)", message)
    commence_time_match = re.search(r"Commence Time:\s*(.+)", message)
    home_team_match = re.search(r"Home Team:\s*(.+)", message)
    away_team_match = re.search(r"Away Team:\s*(.+)", message)
    bookmaker_match = re.search(r"Bookmaker:\s*(\w+)", message)
    market_match = re.search(r"Market:\s*(.+)", message)
    worst_case_devig_match = re.search(r"Worst Case Devig Method:\s*(.+)", message)
    current_over_match = re.search(r"Current Over:\s*(.+)", message)
    current_under_match = re.search(r"Current Under:\s*(.+)", message)
    fair_value_over_match = re.search(r"Fair Value Over:\s*(.+)", message)
    fair_value_under_match = re.search(r"Fair Value Under:\s*(.+)", message)
    over_ev_match = re.search(r"Over EV:\s*(.+)", message)
    under_ev_match = re.search(r"Under EV:\s*(.+)", message)

    # Store the extracted elements in the dictionary
    if sport_match:
        elements["sport"] = sport_match.group(1)
    if commence_time_match:
        elements["commence_time"] = commence_time_match.group(1)
    if home_team_match:
        elements["home_team"] = home_team_match.group(1)
    if away_team_match:
        elements["away_team"] = away_team_match.group(1)
    if bookmaker_match:
        elements["bookmaker"] = bookmaker_match.group(1)
    if market_match:
        elements["market"] = market_match.group(1)
    if worst_case_devig_match:
        elements["worst_case_devig"] = worst_case_devig_match.group(1)
    if current_over_match:
        elements["current_over"] = current_over_match.group(1)
    if current_under_match:
        elements["current_under"] = current_under_match.group(1)
    if fair_value_over_match:
        elements["fair_value_over"] = fair_value_over_match.group(1)
    if fair_value_under_match:
        elements["fair_value_under"] = fair_value_under_match.group(1)
    if over_ev_match:
        elements["over_ev"] = over_ev_match.group(1)
    if under_ev_match:
        elements["under_ev"] = under_ev_match.group(1)
    if current_over_match:
        elements["bet_type"] = "Over"
    elif current_under_match:
        elements["bet_type"] = "Under"
    #USE THIS IF WANT UPDATES ON PREV LINES WHEN MOVED.    
    # player_match = re.search(r"Current (?:Over|Under):\s*(.+)", message)
    # if player_match:
    #     elements["player"] = player_match.group(1)
    player_match = re.search(r"Current (?:Over|Under):\s*([\w\s]+)", message)
    if player_match:
        elements["player"] = player_match.group(1).strip()
    return elements

# async def send_message_to_channel(channel_id, message, image_path=None):
#     message_elements=parse_message(message)
#     current_value = message_elements.get('current_over', message_elements.get('current_under'))
#     fair_value = message_elements.get('fair_value_over', message_elements.get('fair_value_under'))
#     ev_value = message_elements.get('over_ev', message_elements.get('under_ev'))
#     formatted_message = f"""@{message_elements['bookmaker']} Market: {message_elements['market']} 
#     Current {message_elements['bet_type']}:{current_value}. 
#     """
#     try:
#         channel = await bot.fetch_channel(channel_id)
#         if channel is not None:
#             sent_message = await channel.send(formatted_message)

#             # Create a thread for the sent message
#             thread_name = f"Thread for message {sent_message.id}"
#             thread = await sent_message.create_thread(name=thread_name)

#             # Generate and send the image asynchronously
#             if image_path is not None:
#                 watermark_text = get_watermark_text(message)
#                 asyncio.create_task(generate_and_send_image(message,thread, image_path, watermark_text))
#         else:
#             print(f"Channel not found: {channel_id}")
#     except discord.HTTPException as e:
#         print(f"Failed to send message: {e}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
async def send_long_message(ctx, content, max_length=2000):
    if len(content) <= max_length:
        await ctx.send(content)
    else:
        lines = content.splitlines()
        current_message = ""
        for line in lines:
            if len(current_message) + len(line) + 1 > max_length:
                await ctx.send(current_message)
                current_message = ""
            current_message += line + "\n"
        if current_message:
            await ctx.send(current_message)

import asyncio
import subprocess
@bot.command()
async def run(ctx, *args):
    script_path = "oneshot.py"
    command = ["python", script_path] + list(args)

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if stdout:
            await send_long_message(ctx, f"Output:\n{stdout.decode(errors='replace')}")
        if stderr:
            await send_long_message(ctx, f"Error:\n{stderr.decode(errors='replace')}")

    except Exception as e:
        await ctx.send(f"An error occurred while running the script: {e}")

@bot.command()
async def runbook(ctx, *args):
    delay_between_executions = 3  # Set the delay in seconds
    if len(args) < 2:
        await ctx.send("Please provide at least two arguments.")
        return
    market_templates = {
        "fanduel": ["batter_home_runs", "batter_hits", "batter_total_bases",  "batter_rbis", "batter_runs_scored", "batter_singles", "batter_doubles", "batter_triples"],
        "barstool": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_singles", "batter_doubles"],
        "williamhill_us": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_singles", "batter_doubles", "pitcher_strikeouts"],
        "betmgm":["batter_home_runs", "batter_hits", "batter_total_bases",  "batter_rbis", "batter_runs_scored", "batter_singles", "batter_doubles", "pitcher_strikeouts"],
        "wynnbet":["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_singles", "batter_doubles", "pitcher_strikeouts"]
    }
    first_arg = args[0].lower()
    script_path = "oneshot.py"

    if first_arg in market_templates:
        markets = market_templates[first_arg]
        for market in markets:
            command = ["python", script_path, "baseball_mlb",market,first_arg,args[1],"us"]
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                stdout, stderr = await process.communicate()
               
                if stdout:
                    await send_long_message(ctx, f"Output for {market}:\n{stdout.decode(errors='replace')}")
                if stderr:
                    await send_long_message(ctx, f"Error for {market}:\n{stderr.decode(errors='replace')}")
                
            except Exception as e:
                await ctx.send(f"An error occurred while running the script for {market}: {e}")
            await asyncio.sleep(delay_between_executions)
    else:
        await ctx.send("Invalid option. Please provide a valid option (fanduel, draftkings, anotherbookmaker).")

async def send_message_to_channel(channel_id, message, image_path=None):
    message_elements=parse_message(message)
    current_value = message_elements.get('current_over', message_elements.get('current_under'))
    fair_value = message_elements.get('fair_value_over', message_elements.get('fair_value_under'))
    ev_value = message_elements.get('over_ev', message_elements.get('under_ev'))
   
    if message_elements['bookmaker'].capitalize() in role_to_id:
        roleid = role_to_id[message_elements['bookmaker'].capitalize()]

    formatted_message = f"""<@&{roleid}> Market: {message_elements['market']} 
    Current {message_elements['bet_type']}:{current_value}. 
    """
    try:
        print(message_elements['commence_time'])
        commence_time = datetime.strptime(message_elements['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
        
    except:
        pass
    if commence_time <= datetime.utcnow(): #UNIVERSAL TO UNIVERSAL
        print(f"Commence time is not greater than the current time: {commence_time}")
        return
    
    try:
        evthres=float(ev_value)
                # Inside your send_message_to_channel function
        if evthres <= 3:
            channel_id = 1115725994783944754  # freebet
            roleid = role_to_id['FreeBets']
            formatted_message += f"<@&{roleid}>"
            posted_games_set = posted_games_players_freebet
        else:
            if evthres >= 3:
                roleid = role_to_id['Aces']
                formatted_message += f"<@&{roleid}>"
            if evthres >= 5:
                roleid = role_to_id['5%']
                formatted_message += f"<@&{roleid}>"
            if evthres >= 8:
                roleid = role_to_id['nit']
                formatted_message += f"<@&{roleid}>"
            posted_games_set = posted_games_players_other
    except:
        pass
   
    try:
        channel = await bot.fetch_channel(channel_id)
        if channel is not None:
            # player_name = message_elements['current_value'].split()[0]  # Extract player's name from current_value
            game_identifier = f"{message_elements['sport']}_{message_elements['commence_time']}_{message_elements['home_team']}_{message_elements['away_team']}_{message_elements['bookmaker']}_{message_elements['market']}_{message_elements['player']}"
            if game_identifier not in posted_games_set:
                sent_message = await channel.send(formatted_message)
   
                
                # Create a thread for the sent message
                thread_name =  f"""@{message_elements['bookmaker'].capitalize()} Market: {message_elements['market']} 
                Current {message_elements['bet_type']}:{current_value}. 
                """
                # thread = await sent_message.create_thread(name=thread_name)
                thread = await sent_message.create_thread(name=thread_name, auto_archive_duration=1440)
                # Generate and send the image asynchronously
                if image_path is not None:
                    watermark_text = get_watermark_text(message)
                    asyncio.create_task(generate_and_send_image(message,thread, image_path, watermark_text))
                    asyncio.create_task(generate_and_send_caption(message, thread))

                # Add the game identifier to the set
                posted_games_set.add(game_identifier)
        else:
            print(f"Channel not found: {channel_id}")   
    except discord.HTTPException as e:
        print(f"Failed to send message: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(start_socket_server())

from datetime import datetime, timedelta
# def handle_client(conn):
#     try:
#         while True:
#             data = conn.recv(1024)
#             if not data:
#                 break

#             user_id, message, image_path = data.decode('utf-8').split('|', 2)
#             user_id = int(user_id)
#             asyncio.run_coroutine_threadsafe(send_message_to_channel(1115724819091177572, message, image_path), bot.loop)
#             now = datetime.now()
#             conn.sendall(b'Message sent')
#     except Exception as e:
#         print(f"An error occurred while handling client: {e}")
#     finally:
#         conn.close()

# def start_socket_server():
#     host = '127.0.0.1'
#     port = 65432
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind((host, port))
#         s.listen()
#         while True:
#             try:
#                 conn, addr = s.accept()
#                 print(f'Connected by: {addr}')
#                 threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
#             except Exception as e:
#                 print(f"An error occurred while accepting a connection: {e}")

# threading.Thread(target=start_socket_server, daemon=True).start()
import asyncio

async def handle_client(reader, writer):
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            print(f"Received data: {data}")  # Add this print statement
            user_id, message, image_path = data.decode('utf-8').split('|', 2)
            user_id = int(user_id)
            sport=get_sport(message)
            print(sport)
            if(sport=="MLB"):
                channel_id=sportschannels[0]
            elif(sport=="NBA"):
                channel_id=sportschannels[1]
            else:
                channel_id=sportschannels[2]
            await send_message_to_channel(channel_id, message, image_path)
            writer.write(b'Message sent')
            await writer.drain()
    except Exception as e:
        print(f"An error occurred while handling client: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_socket_server():
    host = '127.0.0.1'
    port = 65432
    server = await asyncio.start_server(handle_client, host, port)

    async with server:
        await server.serve_forever()

# Replace the existing threading.Thread with this line
# bot.loop.create_task(start_socket_server())

bot.run(TOKEN)
