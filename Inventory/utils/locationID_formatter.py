from Products.models import Product

import re

def fixLocationIDFormat():
  all_products = Product.objects.all()

  for product in all_products:
        loc = product.location_ID.strip()
        parts = loc.split()

        # Only reformat if exactly 4 parts (e.g., "J B 3 1")
        if len(parts) == 4:
            section = f"0{parts[0].upper()}"
            level = f"0{parts[1].upper()}"
            try:
                vertical = f"{int(parts[2]):02}"
                horizontal = f"{int(parts[3]):02}"
            except ValueError:
                continue  # Skip invalid numeric parts

            new_loc = f"{section}-{level}-{vertical}-{horizontal}"
            print(f"{loc} -> {new_loc}")
            product.location_ID = new_loc
            product.save()

  return