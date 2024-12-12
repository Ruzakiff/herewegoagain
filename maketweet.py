from PIL import Image, ImageDraw, ImageFont
import io
import logging
import requests
import json
import os
import time
import random
import string
import hmac
import hashlib
import base64
import urllib.parse
from dotenv import load_dotenv
import sys
import config

def generate_oauth_headers(url, method="POST"):
    """Generate OAuth headers"""
    # Debug: Print tokens (partially)
    api_key = config.TWITTER_API_KEY
    api_secret = config.TWITTER_API_SECRET
    access_token = config.TWITTER_ACCESS_TOKEN
    access_secret = config.TWITTER_ACCESS_TOKEN_SECRET
    
    print("\nDebug OAuth tokens:")
    print(f"API Key: {api_key[:8]}..." if api_key else "API Key: Missing")
    print(f"API Secret: {api_secret[:8]}..." if api_secret else "API Secret: Missing")
    print(f"Access Token: {access_token[:8]}..." if access_token else "Access Token: Missing")
    print(f"Access Secret: {access_secret[:8]}..." if access_secret else "Access Secret: Missing")
    
    if not all([api_key, api_secret, access_token, access_secret]):
        raise ValueError("Missing required OAuth tokens!")
    
    oauth_timestamp = str(int(time.time()))
    oauth_nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    oauth_params = {
        'oauth_consumer_key': api_key,
        'oauth_token': access_token,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': oauth_timestamp,
        'oauth_nonce': oauth_nonce,
        'oauth_version': '1.0'
    }
    
    # Debug: Print OAuth parameters
    print("\nOAuth Parameters:")
    for k, v in oauth_params.items():
        print(f"{k}: {v}")
    
    base_string = f"{method}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote('&'.join(f'{k}={v}' for k, v in sorted(oauth_params.items())), safe='')}"
    signing_key = f"{api_secret}&{access_secret}"
    
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode()
    
    oauth_params['oauth_signature'] = signature
    
    auth_header = 'OAuth ' + ','.join(f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in oauth_params.items())
    print(f"\nFinal Auth Header (truncated):\n{auth_header[:100]}...")
    
    return auth_header

def upload_media(media_path):
    """Upload media to Twitter and return the media ID."""
    url = "https://upload.twitter.com/1.1/media/upload.json"
    
    # Normalize file path for Windows
    media_path = os.path.normpath(media_path).replace('\\', '/')
    
    try:
        # Get file size and type for debugging
        file_size = os.path.getsize(media_path)
        print(f"\nFile details:")
        print(f"Path: {media_path}")
        print(f"Size: {file_size} bytes")
        
        with open(media_path, 'rb') as file:
            files = {
                'media': file
            }
            
            headers = {
                'Authorization': generate_oauth_headers(url, method="POST")
            }
            
            print("\nSending request to Twitter...")
            response = requests.post(url, headers=headers, files=files)
            
            print(f"\nResponse details:")
            print(f"Status code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Body: {response.text}")
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        print(f"\nTwitter Error:")
                        print(f"Code: {error.get('code')}")
                        print(f"Message: {error.get('message')}")
                
                # Special handling for code 32
                if any(error.get('code') == 32 for error in error_data.get('errors', [])):
                    print("\nAuthentication Error Details:")
                    print("Code 32 typically means invalid credentials")
                    print("Please verify your .env file on Windows:")
                    print("1. No quotes around values")
                    print("2. No spaces around = sign")
                    print("3. No hidden characters (try recreating the file)")
                    print("4. File is saved with UTF-8 encoding")
                    
            if response.status_code == 200:
                return response.json()['media_id_string']
                
            return None
            
    except Exception as e:
        print(f"\nError during upload:")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        return None

def send_tweet(message, media_path=None):
    """Send a tweet with optional media attachment."""
    url = "https://api.twitter.com/2/tweets"
    
    # First upload media if provided
    media_id = None
    if media_path:
        media_id = upload_media(media_path)
        if not media_id:
            raise ValueError("Failed to upload media")
    
    payload = {
        "text": message
    }
    
    # Add media to payload if we have it
    if media_id:
        payload["media"] = {
            "media_ids": [media_id]
        }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': generate_oauth_headers(url)
    }

    response = requests.post(
        url, 
        headers=headers, 
        data=json.dumps(payload)
    )
    
    if response.status_code != 201:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
    
    return response.json()

def verify_environment():
    """Verify environment setup and token format."""
    print("\nEnvironment Verification:")
    
    required_vars = {
        'TWITTER_API_KEY': config.TWITTER_API_KEY,
        'TWITTER_API_SECRET': config.TWITTER_API_SECRET,
        'TWITTER_ACCESS_TOKEN': config.TWITTER_ACCESS_TOKEN,
        'TWITTER_ACCESS_TOKEN_SECRET': config.TWITTER_ACCESS_TOKEN_SECRET
    }
    
    all_good = True
    for var_name, value in required_vars.items():
        if not value:
            print(f"❌ {var_name} is missing")
            all_good = False
        else:
            # Check for common issues
            if value.startswith('"') or value.endswith('"'):
                print(f"❌ {var_name} contains quotes")
                all_good = False
            elif value.startswith("'") or value.endswith("'"):
                print(f"❌ {var_name} contains single quotes")
                all_good = False
            elif value.startswith(" ") or value.endswith(" "):
                print(f"❌ {var_name} contains leading/trailing spaces")
                all_good = False
            else:
                print(f"✓ {var_name} looks good")
    
    return all_good

def text_to_image(text, width=800, height=382, font_size=26):
    # Create black background
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Try different monospace fonts in order of preference
    try:
        font = ImageFont.truetype("OCRAEXT.TTF", font_size)
    except:
        try:
            font = ImageFont.truetype("OCR A Extended.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("Courier New Bold.ttf", font_size)
            except:
                font = ImageFont.truetype("Courier New.ttf", font_size)

    # Word wrap the text
    lines = []
    for original_line in text.splitlines():
        # Add spaces around '@' symbol
        if '@' in original_line:
            original_line = original_line.replace('@', ' @ ')
        
        # Capitalize TD in market text
        if 'td' in original_line.lower():
            original_line = original_line.replace('td', 'TD').replace('Td', 'TD')
        
        # Capitalize bookmaker name after "BOOK: "
        if original_line.startswith('BOOK:'):
            prefix, bookmaker = original_line.split(':', 1)
            original_line = f"{prefix}:{bookmaker.strip().upper()}"
        
        # Skip lines after FV line
        if lines and lines[-1].startswith('FV:'):
            continue
            
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

    # Draw white border with padding
    border_width = 1
    padding = 10  # Pixels from edge
    draw.rectangle([(padding, padding), (width-padding-1, height-padding-1)], 
                  outline=(255, 255, 255), 
                  width=border_width)

    # Draw the text with different colors based on content
    y = 20 + padding  # Adjust starting y position to account for padding
    line_count = 0
    for line in lines:
        # First two lines are always header (date and teams)
        if line_count < 2:
            draw.text((20, y), line, (255, 255, 255), font=font)
            line_count += 1
            # Draw separator line after the second line
            if line_count == 2:
                separator_y = y + font_size + 2
                draw.line([(20, separator_y), (width-20, separator_y)], fill=(255, 255, 255), width=1)
        # Bright green text (LED-like) for BOOK and BET lines
        elif line.startswith("BOOK:") or line.startswith("BET:"):
            draw.text((20, y), line, (34, 255, 34), font=font)
        # Yellow-green for odds and EV
        elif line.startswith("ODDS:") or line.startswith("EV:"):
            draw.text((20, y), line, (173, 255, 47), font=font)
        # White text for everything else
        else:
            draw.text((20, y), line, (255, 255, 255), font=font)
        y += font_size + 5

    return image

def watermark_image(image_data, watermark_text, output_path=None):
    # Open the original image from BytesIO
    original_image = Image.open(image_data).convert("RGBA")
    txt_layer = Image.new("RGBA", original_image.size, (255, 255, 255, 0))

    # Load a font and set its size
    font = ImageFont.truetype("arial.ttf", 65)

    # Create an ImageDraw object
    draw = ImageDraw.Draw(txt_layer)

    # Calculate the size of the watermark text using textbbox
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add padding to the watermark layer
    padding = 20  # Adjust this value if needed
    watermark_layer = Image.new("RGBA", 
                              (text_width + padding * 2, text_height + padding * 2), 
                              (255, 255, 255, 0))

    # Draw the watermark text with padding offset
    draw_watermark = ImageDraw.Draw(watermark_layer)
    draw_watermark.text((padding, padding), watermark_text, 
                       font=font, fill=(242, 242, 242, 128))

    # Rotate the watermark layer by 45 degrees and resize it
    watermark_layer = watermark_layer.rotate(-45, expand=1)
    ratio = min(original_image.width / watermark_layer.width, 
               original_image.height / watermark_layer.height)
    watermark_layer = watermark_layer.resize((int(watermark_layer.width * ratio), 
                                            int(watermark_layer.height * ratio)))

    # Calculate the position to place the watermark (center of the image)
    position = (int((original_image.width - watermark_layer.width) / 2), 
               int((original_image.height - watermark_layer.height) / 2))

    # Paste the watermark layer onto the transparent text layer
    txt_layer.paste(watermark_layer, position, watermark_layer)

    # Combine the original image with the watermark layer
    watermarked_image = Image.alpha_composite(original_image, txt_layer)

    # Instead of saving to file, handle BytesIO if output_path is BytesIO
    if isinstance(output_path, io.BytesIO):
        watermarked_image.save(output_path, format='PNG')
    elif output_path:
        watermarked_image.save(output_path)
    return watermarked_image

if __name__ == "__main__":
    response = send_tweet(
        message="Hello Twitter!",
        media_path="path/to/image.png"
    )
    print(response)