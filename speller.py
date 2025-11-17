import numpy as np
import pylsl
from psychopy import visual, event, monitors, misc
from psychopy import core
from pylsl import StreamInfo, StreamOutlet


class Speller(object):
    """
    A speller with keys and text fields.

    Parameters
    ----------
        size: tuple(int, int)
            The (width, height) of the window in pixels, i.e., resolution
        width: float
            The width of the screen in centimeters
        distance: float
            The distance of the user to the screen in centimeters
        screen: int
            The screen number that is used, default: 0
        fr: int
            The screen refresh rate, default: 60
        window_color: tuple[float, float, float] (default: (0., 0., 0.))
            The background color of the window in (r, g, b)
        control_keys: list[str] (default: ["c"])
            A list of keys that can be used to continue the speller
        quit_keys: list[str] (default: ["q", "escape"])
            A list of keys that can be used to abort the speller
    """

    def __init__(
            self,
            size: tuple,
            width: float,
            distance: float,
            screen: int = 0,
            fr: int = 60,
            window_color: tuple[float, float, float] = (0., 0., 0.),
            control_keys: list[str] = None,
            quit_keys: list[str] = None,
    ):
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
            monitor=self.monitor, screen=screen, units="pix", size=size, color=window_color, fullscr=True)
        self.window.setMouseVisible(False)

        # Initialize keys and fields
        self.keys = dict()
        self.fields = dict()

        # Setup LSL stream
        self.outlet = StreamOutlet(StreamInfo(
            name='MarkerStream', type='Markers', channel_count=1, nominal_srate=0, channel_format=pylsl.cf_string,
            source_id='MarkerStream'))

    def get_size(
            self
    ) -> tuple[int, int]:
        """
        Get the size of the window in pixels, i.e., resolution.

        Returns
        -------
            size: tuple[int, int]:
                The (width, height) of the window in pixels, i.e., resolution
        """
        return self.window.size

    def get_pixels_per_degree(
            self
    ) -> float:
        """
        Get the pixels per degree of visual angle of the window.

        Returns
        -------
            ppd: float:
                The pixels per degree of visual angle
        """
        return misc.deg2pix(degrees=1.0, monitor=self.monitor)

    def get_frame_rate(
            self
    ) -> int:
        """
        Get the frame refresh rate in Hz of the window.

        Returns
        -------
            fr: int
                The frame refresh rate in Hz
        """
        return int(np.round(self.window.getActualFrameRate(infoMsg="")))

    def add_key(
            self,
            name: str,
            size: tuple[int, int],
            pos: tuple[int, int],
            images: list[str] = None,
    ) -> None:
        """
        Add a key to the speller.

        Parameters
        ----------
            name: str
                The name of the key, if none then text is used
            size: tuple[int, int]
                The (width, height) of the key in pixels
            pos: tuple[int, int]
                The (x, y) coordinate of the center of the key, relative to the center of the window
            images: list[str] (default: ["black.png", "white.png"])
                The images of the key. The first image is the default key. Indices will correspond to the 
                values of the codes.
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

    def add_text_field(
            self,
            name: str,
            text: str,
            size: tuple[int, int],
            pos: tuple[int, int],
            field_color: tuple[float, float, float] = (0., 0., 0.),
            text_color: tuple[float, float, float] = (-1., -1., -1.),
            text_size: int = None,
            text_alignment: str = "left",
    ) -> None:
        """
        Add a text field to the speller.

        Parameters
        ----------
            name: str
                The name of the text field, if none then text is used
            text: str
                The text on the text field
            size: tuple[int, int]
                The (width, height) of the text field in pixels
            pos: tuple[int, int]
                The (x, y) coordinate of the center of the text field, relative to the center of the window
            field_color: tuple[float, float, float] (default: (0., 0., 0.))
                The color of the background of the text field
            text_color: tuple[float, float, float] (default: (-1., -1., -1.))
                The color of the text on the text field
            text_size: float (default: 0.5 * size[1])
                The font size of the text
            text_alignment: str (default: "left")
                The alignment of the text, default: "left"
        """
        assert name not in self.fields, "Trying to add a text field with a name that already exists!"
        if text_size is None:
            text_size = 0.5 * size[1]
        self.fields[name] = visual.TextBox2(
            win=self.window, text=text, font='Courier', units="pix", pos=pos, size=size, letterHeight=text_size,
            color=text_color, fillColor=field_color, alignment=text_alignment, autoDraw=True, autoLog=False)

    def set_field_text(
            self,
            name: str,
            text: str,
    ) -> None:
        """
        Set the text of a text field.

        Parameters
        ----------
            name: str
                The name of the text field
            text: str
                The text
        """
        self.fields[name].setText(text)

    def set_text_field_autodraw(
            self,
            name: str,
            autodraw: bool,
    ) -> None:
        """
        Remove a text field.

        Parameters
        ----------
            name: str
                The name of the text field
            autodraw: bool
                The autodraw setting
        """
        self.fields[name].autoDraw = autodraw

    def log(
            self,
            marker: str,
            on_flip: bool = False,
    ) -> None:
        """
        Log a marker.

        Parameters
        ----------
        marker: str
            The marker to log.
        on_flip: bool
            Whether to log on flip or as soon as possible.
        """
        if marker is not None:
            if on_flip:
                self.window.callOnFlip(self.outlet.push_sample, [marker])
            else:
                self.outlet.push_sample([marker])
    
    def run(
            self,
            codes: dict,
            duration: float = None,
            start_marker: str = None,
            stop_marker: str = None,
    ) -> int:
        """
        Present a trial with concurrent flashing of each of the symbols.

        Parameters
        ----------
            codes: dict
                A dictionary with keys being the symbols to flash and the value a list (the code 
                sequence) of integer states (images) for each frame
            duration: float (default: None)
                The duration of the trial in seconds. If the duration is longer than the code
                sequence, it is repeated. If no duration is given, the full length of the first 
                code is used.
            start_marker: str (default: None)
                Marker to send upon first frame flip.
            stop_marker: str (default: None)
                Marker to send upon last frame flip.

        Returns
        -------
            status (int):
                Status flag: 0 for ran normally, 1 for aborted
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
        self.log(stop_marker, on_flip=True)
        self.window.flip()

        # Set autoDraw to True to keep speller visible
        for key in self.keys.values():
            key[0].setAutoDraw(True)

        return 0

    def wait_key(
            self
    ) -> None:
        event.waitKeys(keyList=self.control_keys)

    def is_quit(
            self
    ) -> bool:
        """
        Test if a quit is forced by the user by a key-press.

        Returns
        -------
            flag (bool):
                True is quit forced, otherwise False
        """
        # If quit keys pressed, return True
        if len(event.getKeys(keyList=self.quit_keys)) > 0:
            return True
        return False

    def quit(
            self
    ) -> None:
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
