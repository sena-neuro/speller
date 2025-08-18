from PIL import Image, ImageDraw

WIDTH = 150  # Width of the image (px)
HEIGHT = 150  # Height of the image (px)

TEXT_COLOR = (128, 128, 128)  # Text color (RGB)
FONT_SIZE = 30  # Font size

# The symbols to make images for
KEYS = [
    "!", "@", "#", "$", "%", "^", "&", "asterisk", "(", ")", "_", "+", "backspace",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=",
    "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]", "{", "}",
    "shift", "A", "S", "D", "F", "G", "H", "J", "K", "L", "colon", "quote", "bar", ";", "'", "backslash",
    "tilde", "`", "Z", "X", "C", "V", "B", "N", "M", "comma", ".", "slash", "smaller", "larger", "question",
    "clear", "space", "autocomplete", "speaker"]

# The colors of the keys
KEY_COLORS = ["black", "white", "green"]

# Windows does not allow / , : * ? " < > | ~ in file names
KEY_MAPPING = {
    "slash": "/",
    "comma": ",",
    "colon": ":",
    "asterisk": "*",
    "question": "?",
    "quote": '"',
    "smaller": "<",
    "larger": ">",
    "bar": "|",
    "tilde": "~",
    "backslash": "\\",
    "backspace": "<-",
    "clear": "<<",
    "autocomplete": ">>",
    "shift": "sh",
    "speaker": "sp",
}

# Loop keys
for key in KEYS:

    # No symbol
    if key == "space":
        for color in KEY_COLORS:
            img = Image.new(mode="RGB", size=(WIDTH, HEIGHT), color=color)
            img_draw = ImageDraw.Draw(img)
            img.save(f"{color}.png")

    # Symbol
    else:
        if key in KEY_MAPPING:
            symbol = KEY_MAPPING[key]
        else:
            symbol = key
        for color in KEY_COLORS:
            img = Image.new("RGB", (WIDTH, HEIGHT), color=color)
            img_draw = ImageDraw.Draw(img)
            _, _, text_width, text_height = img_draw.textbbox(xy=(0, 0), text=symbol, font_size=FONT_SIZE)
            x_pos = (WIDTH - text_width) / 2
            y_pos = (HEIGHT - text_height) / 2
            img_draw.text((x_pos, y_pos), symbol, font_size=FONT_SIZE, fill=TEXT_COLOR)
            img.save(f"{key}_{color}.png")
