from lsl_recorder import LSLRecorder
import numpy as np
import os
import psychopy
from psychopy import gui
from speller import Speller
import sys


DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "cvep")
SUBJECT = "01"
SESSION = "01"
RUN = "001"
TASK = "cvep"

PRESENTATION_RATE = 60  # Number of bits to present per second (Hz)
CUE_TIME = 0.8  # Time to present the cue, the target symbol (s)
TRIAL_TIME = 4.2  # Time to present the visual stimulation (s)
ITI_TIME = 0.5  # Inter-trial time, a break in-between trials (s)

SCREEN_FR = 240  # The refresh rate of the monitor (Hz)
SCREEN_ID = 0  # The ID of the monitor (#)
SCREEN_SIZE = (2560, 1600)  # The resolution of the monitor (px, px)
SCREEN_WIDTH = 34.5  # The width of the monitor (cm)
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


# Get task information
dlg = gui.Dlg(title="Task setup")
dlg.addText(text='Session info')
dlg.addField(key='Participant:', initial=SUBJECT)
dlg.addField(key='Age:', initial=99)
dlg.addField(key='Sex:', choices=["Prefer not to answer", "F", "M", "X"])
dlg.addField(key='Session:', initial=SESSION)
dlg.addField(key='Run:', initial=RUN)
dlg.addField(key='Screen refresh rate:', initial=SCREEN_FR)
dlg.addField(key='Screen distance:', initial=SCREEN_DISTANCE)
dlg.addField(key='Cue seconds', initial=CUE_TIME)
dlg.addField(key='Trial seconds', initial=TRIAL_TIME)
dlg.addField(key='Inter-trial seconds', initial=ITI_TIME)
dlg.addField(key='Grid', choices=["Matrix", "QWERTY"])
dlg.addField(key='Codebook', choices=["shifted m-sequence", "modulated Gold codes"])
data = dlg.show()
if dlg.OK:
    subject = data['Participant:']
    age = data['Age:']
    sex = data['Sex:']
    session = data['Session:']
    run = data['Run:']
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
speller.wait_key()
speller.set_text_field_autodraw(name="instructions", autodraw=False)

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

# Add text field at the top of the screen
x_pos = 0
y_pos = SCREEN_SIZE[1] / 2 - TEXT_FIELD_HEIGHT * ppd / 2
speller.add_text_field(
    name="text", text="", size=(SCREEN_SIZE[0], TEXT_FIELD_HEIGHT * ppd), pos=(x_pos, y_pos), field_color=(0, 0, 0),
    text_color=(-1, -1, -1))
speller.set_field_text(name="text", text="Preparing")

# Add stimuli
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

# Set up and start LSL Recorder
try:
    print("Starting recorder")
    recorder = LSLRecorder()
    recorder.set_recorder(root=DATA_DIR, subject=subject, session=session, run=run, task=TASK)
    recorder.update()
    recorder.start()
except Exception as error:
    raise Exception("Error in starting the LSL recorder. Did you start the LSL Recorder App?")

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
out = 0
trials = np.random.permutation(n_stimuli)
for i_trial in range(trials.size):
    # Set target
    target = trials[i_trial]
    target_key = stimuli_to_keys[int(target)]
    print(f"{1 + i_trial:02d}/{trials.size:d}\t{target:02d}\t{target_key:s}")

    # Cue
    highlights[target_key] = [2]
    out = speller.run(
        highlights, CUE_TIME,
        start_marker=f"start_cue;trial={1 + i_trial};target={target};key={target_key}",
        stop_marker=f"stop_cue;trial={1 + i_trial}")
    highlights[target_key] = [0]
    if out > 0:
        break

    # Trial
    out = speller.run(
        stimuli, TRIAL_TIME,
        start_marker=f"start_trial;trial={1 + i_trial}",
        stop_marker=f"stop_trial;trial={1 + i_trial}")
    if out > 0:
        break

    # Inter-trial
    if ITI_TIME > 0:
        out = speller.run(
            highlights, ITI_TIME,
            start_marker=f"start_inter_trial;trial={1 + i_trial}",
            stop_marker=f"stop_inter_trial;trial={1 + i_trial}")
        if out > 0:
            break

# Stop
speller.log(marker=["stop_run"])
speller.set_field_text(name="text", text="Stopping")
print("Stopping")
speller.run(highlights, duration=5.0)

# Stop LSL Recorder
recorder.stop()

# Stop speller
speller.quit()
