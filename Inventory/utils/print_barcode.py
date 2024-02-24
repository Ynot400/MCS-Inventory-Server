import os
from PIL import Image

def print_barcode(image_file_name, product_name):
    file_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'barcodes', image_file_name)
    img = Image.open(file_path)

    # Calculate the new size in pixels (1 inch = 300 pixels)
    new_size = (600, 300)  # 2x1 inches

    # Resize the image
    img_resized = img.resize(new_size)
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop_path, "Resized-2x1-Barcodes-For-Printing")
    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    # Save the resized image
    resized_image_path = os.path.join(folder_path, product_name + "_resized2x1.jpg")
    if os.path.exists(resized_image_path): # if image already exists, print it
       os.system(f'lpr -o fit-to-page -P HP_4500_PRINT "{resized_image_path}"')
    else:
      img_resized = img.resize(new_size)
      img_resized.save(resized_image_path)
      # Print the resized image
      os.system(f'lpr -o fit-to-page -P HP_4500_PRINT "{resized_image_path}"')

if __name__ == "__main__":
  print_barcode('barcode_Tebow.png', 'Tebow')