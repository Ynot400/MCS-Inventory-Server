import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Inventory.settings")  # <-- Change this
django.setup()

from Products.models import Product  # <-- Change this to your app and model
from utils.generate_barcode import generate_barcode_and_save  # <-- Adjust to your barcode function

def regenerate_all_barcodes():
    products = Product.objects.all()
    print(f"Found {products.count()} products. Generating barcodes...\n")

    for product in products:
        try:
            generate_barcode_and_save(
                barcode_value=product.barcode,
                product_title=product.title,
                part_number=product.product_ID,
                location=product.location_ID,
                vendor=product.vendor
            )
            print(f"✅ {product.title}")
        except Exception as e:
            print(f"❌ Failed to generate for {product.title}: {e}")

    print("\nDone.")

if __name__ == "__main__":
    regenerate_all_barcodes()
