from PIL import Image, ImageDraw, ImageFont
import io

import tweepy

def post_tweet_with_image(consumer_key, consumer_secret, access_token, access_token_secret, image_path, tweet_text):
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    # Create API object
    api = tweepy.API(auth)

    # Upload image
    media = api.media_upload(image_path)

    # Post tweet with image
    tweet = api.update_status(status=tweet_text, media_ids=[media.media_id])

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
    # Test text_to_image function
    test_text = """Wednesday October 11, 07:07PM EST
Houston Astros @ Minnesota Twins

BOOK: Betrivers
BET: Jorge Polanco Over 0.5 Batter Runs Scored
ODDS: +108
EV: 4.00%

FV: -100.00
DEVIG: Additive Devig
DEVIG LINES: -115/-115"""
    
    # Create and save the test image
    image = text_to_image(test_text)
    image.save("test_bet.png")
    
    # Test watermark with file
    with open("test_bet.png", 'rb') as img_file:
        img_bytes = io.BytesIO(img_file.read())
        watermarked = watermark_image(img_bytes, "WATERMARK TEST")
        watermarked.save("test_watermarked.png")
    
    print("Test images have been created: 'test_bet.png' and 'test_watermarked.png'")