import numpy as np
import os
import psychopy
import pylsl
from psychopy import visual, event, monitors, misc
from psychopy import core, gui
from pylsl import StreamInfo, StreamOutlet
import sys


PRESENTATION_RATE = 60  # Number of bits to present per second (Hz)
CUE_TIME = 0.8  # Time to present the cue, the target symbol (s)
TRIAL_TIME = 4.2  # Time to present the visual stimulation (s)
ITI_TIME = 0.5  # Inter-trial time, a break in-between trials (s)

SCREEN_FR = 60  # 240  # The refresh rate of the monitor (Hz)
SCREEN_ID = 1  # The ID of the monitor (#)
SCREEN_SIZE = (1920, 1080)  # (2560, 1600)  # The resolution of the monitor (px, px)
SCREEN_WIDTH = 53.5  # 34.5  # The width of the monitor (cm)
SCREEN_DISTANCE = 100.0  # The distance of the monitor to the participant (cm)

TEXT_FIELD_HEIGHT = 3.0  # Height of the text field on top of the screen (visual degrees)

KEY_WIDTH = 2.5  # The width of the keys (visual degrees)
KEY_HEIGHT = 2.5  # The height of the keys (visual degrees)
KEY_SPACE = 0.5  # The distance between keys (visual degrees)
KEY_COLORS = ["black", "white", "green"]  # The colors for the keys

# The speller grid to present
QWERTY_KEYS = [
    ["!", "@", "#", "$", "%", "^", "&", "asterisk", "(", ")", "_", "=", "backspace"],  # 13
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}"],  # 12
    ["shift", "A", "S", "D", "F", "G", "H", "J", "K", "L", "colon", "quote", "bar"],  # 13
    ["tilde", "Z", "X", "C", "V", "B", "N", "M", "smaller", "larger", "question"],  # 11
    ["clear", "space",  "autocomplete", "speaker"],  # 4
]
MATRIX_KEYS = [
    ["A", "B", "C", "D", "E", "F", "G", "H"],  # 8
    ["I", "J", "K", "L", "M", "N", "O", "P"],  # 8
    ["Q", "R", "S", "T", "U", "V", "W", "X"],  # 8
    ["Y", "Z", "1", "2", "3", "4", "5", "6"],  # 8
]

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


class Speller(object):
    """
    A speller with keys and text fields.
    """

    def __init__(self, size, width, distance, screen=0, fr=60, window_color=(0, 0, 0), quit_keys=None):
        """
        Create a speller.

        Args:
            size (array-like): 
                The (width, height) of the window in pixels, i.e., resolution
            width (float):
                The width of the screen in centimeters
            distance (float):
                The distance of the user to the screen in centimeters
            screen (int):
                The screen number that is used, default: 0
            fr (int):
                The screen refresh rate, default: 60
            window_color (array-like):
                The background color of the window, default: (0, 0, 0)
            quit_keys (list):
                A list of keys that can be used to abort the speller, default: ["q", "escape"]
        """
        self.fr = fr
        if quit_keys is None:
            self.quit_keys = ["q", "escape"]
        else:
            self.quit_keys = quit_keys

        # Set up monitor (sets pixels per degree)
        self.monitor = monitors.Monitor(name="testMonitor", width=width, distance=distance)
        self.monitor.setSizePix(size)

        # Set up window
        self.window = visual.Window(
            monitor=self.monitor, screen=screen, units="pix", size=size, color=window_color, fullscr=True,
            waitBlanking=False, allowGUI=False)
        self.window.setMouseVisible(False)

        # Initialize keys and fields
        self.keys = dict()
        self.fields = dict()

        # Setup LSL stream
        self.outlet = StreamOutlet(StreamInfo(
            name='MarkerStream', type='Markers', channel_count=1, nominal_srate=0, channel_format=pylsl.cf_string,
            source_id='MarkerStream'))

    def get_size(self):
        """
        Get the size of the window in pixels, i.e., resolution.

        Returns:
            (tuple):
                The (width, height) of the window in pixels, i.e., resolution
        """
        return self.window.size

    def get_pixels_per_degree(self):
        """
        Get the pixels per degree of visual angle of the window.

        Returns:
            (float): 
                The pixels per degree of visual angle
        """
        return misc.deg2pix(degrees=1.0, monitor=self.monitor)

    def get_frame_rate(self):
        """
        Get the frame refresh rate in Hz of the window.

        Returns:
            (int):
                The frame refresh rate in Hz
        """
        return int(np.round(self.window.getActualFrameRate(infoMsg="")))

    def add_key(self, name, size, pos, images=None):
        """
        Add a key to the speller.

        Args:
            name (str):
                The name of the key, if none then text is used
            size (array-like):
                The (width, height) of the key in pixels
            pos (array-like):
                The (x, y) coordinate of the center of the key, relative to the center of the window
            images (array-like):
                The images of the key. The first image is the default key. Indices will correspond to the 
                values of the codes. Default: ["black.png", "white.png"]
        """
        assert name not in self.keys, "Trying to add a box with a name that already exists!"
        if images is None:
            images = ["black.png", "white.png"]
        self.keys[name] = []
        for image in images:
            self.keys[name].append(visual.ImageStim(
                win=self.window, image=image, units="pix", pos=pos, size=size, autoLog=False))

        # Set autoDraw to True for first default key to keep app visible
        self.keys[name][0].setAutoDraw(True)

    def add_text_field(self, name, text, size, pos, field_color=(0, 0, 0), text_color=(-1, -1, -1), text_size=None,
                       text_alignment="left"):
        """
        Add a text field to the speller.

        Args:
            name (str):
                The name of the text field, if none then text is used
            text (str):
                The text on the text field
            size (array-like):
                The (width, height) of the text field in pixels
            pos (array-like):
                The (x, y) coordinate of the center of the text field, relative to the center of the window
            field_color (array-like):
                The color of the background of the text field, default: (0, 0, 0)
            text_color (array-like):
                The color of the text on the text field, default: (-1, -1, -1)
            text_size (float):
                The font size of the text, default: 0.5 * size[1]
            text_alignment (str):
                The alignment of the text, default: "left"
        """
        assert name not in self.fields, "Trying to add a text field with a name that already exists!"
        if text_size is None:
            text_size = 0.5 * size[1]
        self.fields[name] = self.fields[name] = visual.TextBox2(
            win=self.window, text=text, font='Courier', units="pix", pos=pos, size=size, letterHeight=text_size,
            color=text_color, fillColor=field_color, alignment=text_alignment, autoDraw=True, autoLog=False)

    def set_field_text(self, name, text):
        """
        Set the text of a text field.

        Args:
            name (str):
                The name of the text field
            text (str):
                The text
        """
        self.fields[name].setText(text)
        self.window.flip()

    def set_text_field_autodraw(self, name, autodraw):
        """
        Remove a text field.

        Args:
            name (str):
                The name of the text field
            autodraw (bool):
                The autodraw setting, either True or False
        """
        self.fields[name].autoDraw = autodraw

    def log(self, marker, on_flip=False):
        if marker is not None:
            if not isinstance(marker, list):
                marker = [marker]
            if on_flip:
                self.window.callOnFlip(self.outlet.push_sample, marker)
            else:
                self.outlet.push_sample(marker)    
    
    def run(self, codes, duration=None, start_marker=None, stop_marker=None):
        """
        Present a trial with concurrent flashing of each of the symbols.

        Args:
            codes (dict): 
                A dictionary with keys being the symbols to flash and the value a list (the code 
                sequence) of integer states (images) for each frame
            duration (float):
                The duration of the trial in seconds. If the duration is longer than the code
                sequence, it is repeated. If no duration is given, the full length of the first 
                code is used. Default: None
            start_marker (str):
                Marker to send upon first frame flip.
            stop_marker (str):
                Marker to send upon last frame flip.
        """
        # Set number of frames
        if duration is None:
            n_frames = len(codes[list(codes.keys())[0]])
        else:
            n_frames = int(duration * self.fr)

        # Set autoDraw to False for full control
        for key in self.keys.values():
            key[0].setAutoDraw(False)

        # Send start marker
        self.log(start_marker, on_flip=True)

        # Loop frame flips
        for i in range(n_frames):

            # Check quiting
            if i % 60 == 0:
                if self.is_quit():
                    self.quit()

            # Draw keys with color depending on code state
            for name, code in codes.items():
                self.keys[name][int(code[i % len(code)])].draw()
            self.window.flip()

        # Send stop marker
        self.log(stop_marker)

        # Set autoDraw to True to keep speller visible
        for key in self.keys.values():
            key[0].setAutoDraw(True)
        self.window.flip()

    def is_quit(self):
        """
        Test if a quit is forced by the user by a key-press.

        Returns:
            (bool): 
                True is quit forced, otherwise False
        """
        # If quit keys pressed, return True
        if len(event.getKeys(keyList=self.quit_keys)) > 0:
            return True
        return False

    def quit(self):
        """
        Quit the speller.
        """
        self.window.setMouseVisible(True)
        self.window.close()
        core.quit()


def main():
    # Get user information
    global SCREEN_FR, SCREEN_DISTANCE, CUE_TIME, TRIAL_TIME, ITI_TIME
    dlg = gui.Dlg(title="Task setup")
    dlg.addText(text='Participant info')
    dlg.addField(key='ID:', initial="sub-99")
    dlg.addField(key='Age:', initial=99)
    dlg.addField(key='Sex:', choices=["Prefer not to answer", "F", "M", "X"])
    dlg.addText(text='Task info')
    dlg.addField(key='Screen refresh rate:', initial=SCREEN_FR)
    dlg.addField(key='Screen distance:', initial=SCREEN_DISTANCE)
    dlg.addField(key='Cue seconds', initial=CUE_TIME)
    dlg.addField(key='Trial seconds', initial=TRIAL_TIME)
    dlg.addField(key='Inter-trial seconds', initial=ITI_TIME)
    dlg.addField(key='Grid', choices=["Matrix", "QWERTY"])
    dlg.addField(key='Codebook', choices=["shifted m-sequence", "modulated Gold codes"])
    data = dlg.show()
    if dlg.OK:
        subject = data['ID:']
        age = data['Age:']
        sex = data['Sex:']
        SCREEN_FR = data['Screen refresh rate:']
        SCREEN_DISTANCE = data['Screen distance:']
        CUE_TIME = data['Cue seconds']
        TRIAL_TIME = data['Trial seconds']
        ITI_TIME = data['Inter-trial seconds']
        grid = data['Grid']
        codebook = data['Codebook']
    else:
        raise Exception('User cancelled')

    # Set grid
    if grid.lower() == "matrix":
        KEYS = MATRIX_KEYS
    elif grid.lower() == "qwerty":
        KEYS = QWERTY_KEYS
    else:
        raise Exception("Unknown grid:", grid)

    # Set codes
    n_stimuli = sum([len(row) for row in KEYS])
    if codebook.lower() == "shifted m-sequence":
        codes = np.load(os.path.join("codes", "shifted_m_sequence.npz"))["codes"]
        if grid.lower() == "matrix":
            codes = codes[::2, :]  # select the proper lags
    elif codebook.lower() == "modulated gold codes":
        codes = np.load(os.path.join("codes", "modulated_gold_codes.npz"))["codes"]
    else:
        raise Exception("Unknown codebook:", codebook)

    # Setup speller
    speller = Speller(
        size=SCREEN_SIZE, width=SCREEN_WIDTH, distance=SCREEN_DISTANCE, screen=SCREEN_ID, fr=SCREEN_FR)
    ppd = speller.get_pixels_per_degree()

    # Show instructions
    speller.add_text_field(
        name="instructions", text="", size=SCREEN_SIZE, pos=(0, 0), field_color=(0, 0, 0), text_color=(-1, -1, -1),
        text_size=0.6 * ppd, text_alignment="center")
    instructions = (
        "You will be presented with a grid of symbols.\n"
        f"A target symbol will be highlighted in green for {CUE_TIME:.1f} s.\n"
        f"Then, all symbols, also the target, will flash for {TRIAL_TIME:.1f} s.\n"
        "During that flashing, keep fixating your eyes at the target symbol.\n"
        f"You will fixate at each of {n_stimuli} symbols once, in random order.\n"
        "During the entire task, do not move and minimize eye blinks.\n"
        f"This task takes about {n_stimuli * (CUE_TIME + TRIAL_TIME + ITI_TIME) / 60:.1f} min.\n"
    )
    speller.set_field_text(name="instructions", text=instructions)
    print("Presenting instructions")
    event.waitKeys(keyList=["c"])
    speller.set_text_field_autodraw(name="instructions", autodraw=False)

    # Add text field at the top of the screen
    x_pos = 0
    y_pos = SCREEN_SIZE[1] / 2 - TEXT_FIELD_HEIGHT * ppd / 2
    speller.add_text_field(
        name="text", text="", size=(SCREEN_SIZE[0], TEXT_FIELD_HEIGHT * ppd), pos=(x_pos, y_pos), field_color=(0, 0, 0),
        text_color=(-1, -1, -1))

    # Add keys
    for y in range(len(KEYS)):
        for x in range(len(KEYS[y])):
            x_pos = int((x - len(KEYS[y]) / 2 + 0.5) * (KEY_WIDTH + KEY_SPACE) * ppd)
            y_pos = int(-(y - len(KEYS) / 2) * (KEY_HEIGHT + KEY_SPACE) * ppd - TEXT_FIELD_HEIGHT * ppd)
            if grid.lower() == "qwerty":
                if y == 0 or y == 1:
                    x_pos += int(0.25 * KEY_WIDTH * ppd)
                elif y == 3 or y == 4:
                    x_pos -= int(0.5 * KEY_WIDTH * ppd)
            if KEYS[y][x] == "space":
                images = [os.path.join("images", f"{color}.png") for color in KEY_COLORS]
            else:
                images = [os.path.join("images", f"{KEYS[y][x]}_{color}.png") for color in KEY_COLORS]
            speller.add_key(
                name=KEYS[y][x], images=images, size=(int(KEY_WIDTH * ppd), int(KEY_HEIGHT * ppd)), pos=(x_pos, y_pos))

    # Add codes
    codes = np.repeat(codes, int(SCREEN_FR / PRESENTATION_RATE), axis=1)  # upsample to frame refresh rate
    stimuli = dict()
    stimuli_to_keys = dict()
    i = 0
    for row in KEYS:
        for key in row:
            stimuli[key] = codes[i, :].tolist()
            stimuli_to_keys[i] = key
            i += 1

    # Set highlights
    highlights = dict()
    for row in KEYS:
        for key in row:
            highlights[key] = [0]

    # Wait
    speller.set_field_text(name="text", text="Waiting to start")
    print("Waiting to start")
    event.waitKeys(keyList=["c"])

    # Log version information
    speller.log(f"python_version;{sys.version_info}")
    speller.log(f"psychopy_version;{psychopy.__version__}")

    # Log settings
    speller.log(
        f"settings;subject={subject};age={age};sex={sex};" +
        f"screen_fr={SCREEN_FR};screen_distance={SCREEN_DISTANCE};" +
        f"cue_time={CUE_TIME};trial_time={TRIAL_TIME};iti_time={ITI_TIME};" +
        f"grid={grid.lower()};codebook={codebook.lower()}")

    # Start
    speller.log(marker=["start_run"])
    speller.set_field_text(name="text", text="Starting")
    print("Starting")
    speller.run(highlights, duration=5.0)
    speller.set_field_text(name="text", text="")

    # Loop trials
    trials = np.random.permutation(n_stimuli)
    for i_trial in range(trials.size):
        # Set random target
        target = trials[i_trial]
        target_key = stimuli_to_keys[int(target)]
        print(f"{1 + i_trial:02d}/{trials.size:d}\t{target:02d}\t{target_key:s}")

        # Cue
        highlights[target_key] = [2]
        speller.run(
            highlights, CUE_TIME,
            start_marker=f"start_cue;trial={i_trial};target={target};key={target_key}",
            stop_marker=f"stop_cue;trial={i_trial}")
        highlights[target_key] = [0]

        # Trial
        speller.run(
            stimuli, TRIAL_TIME,
            start_marker=f"start_trial;trial={i_trial}",
            stop_marker=f"stop_trial;trial={i_trial}")

        # Inter-trial
        if ITI_TIME > 0:
            speller.run(
                highlights, ITI_TIME,
                start_marker=f"start_inter_trial;trial={i_trial}",
                stop_marker=f"stop_inter_trial;trial={i_trial}")

    # Stop
    speller.log(marker=["stop_run"])
    speller.set_field_text(name="text", text="Stopping")
    print("Stopping")
    speller.run(highlights, duration=5.0)

    # Wait
    speller.set_field_text(name="text", text="Waiting to stop")
    event.waitKeys(keyList=["c"])
    speller.set_field_text(name="text", text="")

    # Stop
    speller.quit()


if __name__ == "__main__":
    main()
