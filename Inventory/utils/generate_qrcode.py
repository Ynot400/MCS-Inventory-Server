import qrcode
import os

def generateQR(username, password):
  combined_data = f"{username}:{password}"
  qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
    )
  qr.add_data(combined_data)
  try:
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
  except Exception as e:
    print(f"QR Code generation failed: {e}")
  desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
  folder_path = os.path.join(desktop_path, "Employee-QRCodes")

  # Create the folder if it doesn't exist
  if not os.path.exists(folder_path):
      os.makedirs(folder_path)
  # Generate the filename
  filename = f"Employee-{username}-QRCode.png"
  # Define the full filepath
  filepath = os.path.join(folder_path, f"{filename}")
  # Save the barcode as a PNG image
  img.save(filepath)

if __name__ == "__main__":
   test = "testing"
   passw = "1234nivwkdbfkc8392432bhwfdekhjb!"
   generateQR(test, passw)
