import os
import barcode
from barcode.writer import ImageWriter
from PIL import Image


def generate_barcode_and_save(barcode_value, product_title):
    barcode_format = barcode.get_barcode_class('ean13')
   
    generated = barcode_format(str(barcode_value), no_checksum=False, writer=ImageWriter())
   
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    folder_path = os.path.join(desktop_path, "barcodes")

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Generate the filename
    filename = f"barcode_{product_title}"

    # Define the full filepath
    filepath = os.path.join(folder_path, f"{filename}")

    # Save the barcode as a PNG image
    generated.save(filepath)
     
    return 0

if __name__ == "__main__":
    # Example usage
    barcode_value = '012345678912'
    product_title = 'ExampleyProduct23'

    generate_barcode_and_save(barcode_value, product_title)
