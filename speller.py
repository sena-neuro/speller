import numpy as np
import pylsl
from psychopy import visual, event, monitors, misc
from psychopy import core
from pylsl import StreamInfo, StreamOutlet


class Speller(object):
    """
    A speller with keys and text fields.
    """

    def __init__(self, size, width, distance, screen=0, fr=60, window_color=(0, 0, 0), control_keys=None,
                 quit_keys=None):
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
            control_keys (list):
                A list of keys that can be used to continue the speller, default: ["c"]
            quit_keys (list):
                A list of keys that can be used to abort the speller, default: ["q", "escape"]
        """
        self.fr = fr
        if control_keys is None:
            self.control_keys = ["c"]
        else:
            self.control_keys = control_keys
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

        Returns:
            (int) Status flag, 0 for ran normally, 1 for aborted
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
                    return 1

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

        return 0

    def wait_key(self):
        event.waitKeys(keyList=self.control_keys)

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


if __name__ == "__main__":
    print("starting")
    speller = Speller(size=(1920, 1080), width=53.5, distance=50, screen=1, fr=60)
    speller.add_text_field(name="text", text="test", size=(1920, 400), pos=(0, 340), text_alignment="center")
    speller.add_key(name="test", size=(100, 100), pos=(0, 0), images=["images/black.png", "images/white.png"])
    print("waiting")
    speller.wait_key()
    print("flashing")
    speller.run(codes={"test": 5 * 60 * [1, 0]}, start_marker="start", stop_marker="stop")
    print("closing")
    speller.quit()
