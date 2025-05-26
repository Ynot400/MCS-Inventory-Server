import os
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

def sanitize_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', "'"]
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

def generate_barcode_and_save(barcode_value, product_title, part_number, location):
    barcode_format = barcode.get_barcode_class('ean13')
   
    generated = barcode_format(str(barcode_value), no_checksum=False, writer=ImageWriter())
   
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop_path, "barcodes")

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Sanitize the product_title
    sanitized_title = sanitize_filename(product_title)

    # Generate the filename
    filename = f"barcode_{sanitized_title}"

    # Define the full filepath
    filepath = os.path.join(folder_path, f"{filename}")

    # Save the barcode as a PNG image
    generated.save(filepath)
    # Open the image again and get a drawing context
    
    # Open the image again and get a drawing context
    img = Image.open(filepath + '.png')
    draw = ImageDraw.Draw(img)

    # Define the text
    text = f"{product_title} {part_number} {location}"

    # Get the width and height of the image
    img_width = img.width

    # Define the maximum width and height of the text
    max_text_width = img_width - 8   # adjust this value as needed


    # Define the initial font size
    font_size = 40  # adjust this value as needed

    # Load the font
    font = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size) 

    # Get the width and height of the text
    text_width = font.getlength(text)

    # Adjust the font size until the text fits within the maximum width and height
    while text_width > max_text_width:
        font_size -= 1
        font = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size) 
        text_width = font.getlength(text)

    # Calculate the position of the text
    text_x = 8
    text_y = 235

    # Draw the text on the image
    draw.text((text_x, text_y), text, font=font, fill="black")  # adjust the fill color as needed

    # Save the image again
    img.save(filepath + '.png')

    return 0

if __name__ == "__main__":
    # Example usage
    barcode_value = '012345678912'
    product_title = 'Da Awewsomeness'
    part_number = "23984723894"
    location = "3832bd"

    generate_barcode_and_save(barcode_value, product_title, part_number, location)