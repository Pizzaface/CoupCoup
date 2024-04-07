import random
import secrets


def random_hex_color_code():
    # Generate a random number for alpha, red, green, and blue components
    # Each component is an integer in the range 0 to 255
    alpha = secrets.randbelow(50)
    red = secrets.randbelow(256)
    green = secrets.randbelow(256)
    blue = secrets.randbelow(256)

    # Convert each component to a hexadecimal string and format it to 2 characters
    # Combine the components into a single string
    argb_color = f'{alpha:02X}{red:02X}{green:02X}{blue:02X}'

    font_color = (
        'FF000000'
        if (red * 0.299 + green * 0.587 + blue * 0.114) > 120
        else 'FFFFFFFF'
    )
    return argb_color, font_color
