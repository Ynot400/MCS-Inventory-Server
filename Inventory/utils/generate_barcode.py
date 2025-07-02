import os
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont, ImageOps

def sanitize_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', "'"]
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename

def generate_barcode_and_save(barcode_value, product_title, part_number, location, vendor=None):
    barcode_format = barcode.get_barcode_class('ean13')
   
    generated = barcode_format(str(barcode_value), no_checksum=False, writer=ImageWriter())
   
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop_path, "barcodes")

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Sanitize the product_title
    sanitized_title = sanitize_filename(product_title)
    if part_number is not None:
        sanitized_partNum = sanitize_filename(part_number)

        # Generate the filename
        filename = f"barcode_{sanitized_title}_{sanitized_partNum}"
    else:
        if vendor is not None:
            sanitized_vendor = sanitize_filename(vendor)
            filename = f"barcode_{sanitized_title}_{sanitized_vendor}_{location}"
        else:
            filename = f"barcode_{sanitized_title}_{location}"

    # Define the full filepath
    filepath = os.path.join(folder_path, f"{filename}")

    # Save the barcode as a PNG image
    generated.save(filepath, options={"write_text": False})
    # Open the image again and get a drawing context
    
    # Open the image again and get a drawing context
    img = Image.open(filepath + '.png')
    padding_bottom = 100
    padding_length = 38

    padded_img = ImageOps.expand(img, border=(0, 0, 0, padding_bottom), fill='white')
    padded_img = ImageOps.expand(padded_img, border=(padding_length, 0, padding_length, 0), fill='white')

    draw = ImageDraw.Draw(padded_img)
    # print(f"Image size: {padded_img.size}")

    # Define the text
    text1 = f"{product_title}"
    text2 = f"{part_number}  {location}" if part_number else f"{sanitized_vendor}  {location}"
    # Get the width and height of the image
    img_width = padded_img.width
    # Define the maximum width and height of the text
    max_text_width = img_width   # adjust this value as needed


    # Define the initial font size
    font_size1 = 70  # adjust this value as needed
    font_size2 = 60  # adjust this value as needed


    # Load the font
    font1 = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size1)
    font2 = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size2) 

    # Get the width and height of the text
    text1_width = font1.getlength(text1)
    text2_width = font2.getlength(text2)
    # print(f"Text1 width: {text1_width}, Text2 width: {text2_width}")

    # Adjust the font size until the text fits within the maximum width and height
    while text1_width > max_text_width:
        font_size1 -= 1
        font1 = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size1) 
        text1_width = font1.getlength(text1)
    
    while text2_width > max_text_width:
        font_size2 -= 1
        font2 = ImageFont.truetype('/Library/Fonts/Arial.ttf', font_size2) 
        text2_width = font2.getlength(text2)
    # print(f"Final font size fo text1: {font_size1}, Final font size for text2: {font_size2}")
    # print(f"Text1 width: {text1_width}, Text2 width: {text2_width}")


    # Calculate the position of the text
    text_x = 0
    text_y = 180

    # Draw the text on the image
    draw.text((text_x, text_y), text1, font=font1, fill="black")  # adjust the fill color as needed
    draw.text((text_x, text_y + 55), text2, font=font2, fill="black")  # adjust the fill color as needed

    # Save the image again
    padded_img.save(filepath + '.png')

    return 0

if __name__ == "__main__":
    # Example usage
    barcode_value = '1242848260294'
    product_title = '3" 1/2" Elbow'
    part_number = "1-2323 aknna w"
    location = "0K-0B-06-08"

    generate_barcode_and_save(barcode_value, product_title, part_number, location)