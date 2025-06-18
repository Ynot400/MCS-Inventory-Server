import os
import time
from PIL import Image

def sanitize_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', "'"]
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename


def print_barcode(product_name, part_number, location,  num_copies=1):
    product_name = sanitize_filename(product_name)
    if part_number is not None:
        part_num = sanitize_filename(part_number)
        image_file_name = f"barcode_{product_name}_{part_num}.png"
    else:
        image_file_name = f"barcode_{product_name}_{location}.png"
    file_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'barcodes', image_file_name)
    # img = Image.open(file_path)
    

    # # Calculate the new size in pixels (1 inch = 300 pixels)
    # new_size = (600, 300)  # 2x1 inches
    # # Resize the image
    # img_resized = img.resize(new_size)
    # desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    # folder_path = os.path.join(desktop_path, "Resized-2x1-Barcodes-For-Printing")
    # # Create the folder if it doesn't exist
    # if not os.path.exists(folder_path):
    #     os.makedirs(folder_path)
    # # Save the resized image
    # product_name = sanitize_filename(product_name)
    # resized_image_path = os.path.join(folder_path, product_name + "_resized2x1.jpg")
   
    # img_resized = img.resize(new_size)
    # img_resized.save(resized_image_path)
    # os.system(f'lpr -o scaling=100 -P Rollo_X1040 "{resized_image_path}"')
    for _ in range(num_copies):
        os.system(f'lpr -o media=2x1 "{file_path}"')
        time.sleep(0.3)

if __name__ == "__main__":
  print_barcode('Tebow')