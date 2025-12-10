from pathlib import Path
from lsl_recorder import LSLRecorder, find_lsl_recorder_app
import numpy as np
import os
import psychopy
from psychopy import gui, data
from speller import Speller
import sys
import subprocess
import itertools


# LSL Recorder configuration
# Priority: environment variable > auto-detection
LSL_RECORDER_APP_DIR = os.environ.get("LSL_RECORDER_APP") or find_lsl_recorder_app()

STIMULI_DIR = Path() / "images"

DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "cvep")
SUBJECT = "01"  # subject identifier
SESSION = "01"  # session identifier
RUN = 1  # run identifier
TASK = "cvep"  # task identifier

PRESENTATION_RATE = 60  # Number of bits to present per second (Hz)
CUE_TIME = 0.8  # Time to present the cue, the target symbol (s)
TRIAL_TIME = 4.2  # Time to present the visual stimulation (s)
ITI_TIME = 0.5  # Inter-trial time, a break in-between trials (s)

SCREEN_FR = 60  # The refresh rate of the monitor (Hz)
SCREEN_ID = 0  # The ID of the monitor (#)
SCREEN_SIZE = (1920, 1080)  # The resolution of the monitor (px, px)
SCREEN_WIDTH = 53  # The width of the monitor (cm)
SCREEN_DISTANCE = 60.0  # The distance of the monitor to the participant (cm)

TEXT_FIELD_HEIGHT = (
    3.0  # Height of the text field on top of the screen (visual degrees)
)

KEY_WIDTH = 4  # The width of the keys (visual degrees)
KEY_HEIGHT = 4  # The height of the keys (visual degrees)
KEY_SPACE = 0.8  # The distance between keys (visual degrees)

# ON_COLOR = "black"
# OFF_COLOR = "black"
WINDOW_COLOR = "black"
ON_COLOR = "grating"
OFF_COLOR = "gray"
CUE_COLOR = "green"
KEY_COLORS = [OFF_COLOR, CUE_COLOR, ON_COLOR]  # The colors for the keys

# The speller grid to present
QWERTY_KEYS = [
    [
        "!",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "asterisk",
        "(",
        ")",
        "_",
        "=",
        "backspace",
    ],  # 13
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}"],  # 12
    [
        "shift",
        "A",
        "S",
        "D",
        "F",
        "G",
        "H",
        "J",
        "K",
        "L",
        "colon",
        "quote",
        "bar",
    ],  # 13
    ["tilde", "Z", "X", "C", "V", "B", "N", "M", "smaller", "larger", "question"],  # 11
    ["clear", "space", "autocomplete", "speaker"],  # 4
]
MATRIX_KEYS = [
    ["A", "B", "C", "D", "E", "F", "G", "H"],  # 8
    ["I", "J", "K", "L", "M", "N", "O", "P"],  # 8
    ["Q", "R", "S", "T", "U", "V", "W", "X"],  # 8
    ["Y", "Z", "space", "backspace", "comma", "dot", "question", "clear"],  # 8
]

# Windows does not allow / , : * ? " < > | ~ in file names
KEY_MAPPING = {
    "space": "􁁺",
    "dot": ".",
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
    "backspace": "􀆛",
    "clear": "􁝀",
    "autocomplete": ">>",
    "shift": "sh",
    "speaker": "sp",
}


# Get task information
dlg = gui.Dlg(title="Task setup")
dlg.addText(text="Session info")
dlg.addField(key="Participant:", initial=SUBJECT)
dlg.addField(key="Age:", initial=99)
dlg.addField(key="Sex:", choices=["Prefer not to answer", "F", "M", "X"])
dlg.addField(key="Session:", initial=SESSION)
dlg.addField(key="Run:", initial=RUN)
dlg.addField(key="Screen refresh rate:", initial=SCREEN_FR)
dlg.addField(key="Screen distance:", initial=SCREEN_DISTANCE)
dlg.addField(key="Cue seconds", initial=CUE_TIME)
dlg.addField(key="Trial seconds", initial=TRIAL_TIME)
dlg.addField(key="Inter-trial seconds", initial=ITI_TIME)
dlg.addField(key="Grid", choices=["Matrix", "QWERTY"])
dlg.addField(key="Codebook", choices=["shifted m-sequence", "modulated Gold codes"])
data_ = dlg.show()
if dlg.OK:
    subject = data_["Participant:"]
    age = data_["Age:"]
    sex = data_["Sex:"]
    session = data_["Session:"]
    run = int(data_["Run:"])
    SCREEN_FR = data_["Screen refresh rate:"]
    SCREEN_DISTANCE = data_["Screen distance:"]
    CUE_TIME = data_["Cue seconds"]
    TRIAL_TIME = data_["Trial seconds"]
    ITI_TIME = data_["Inter-trial seconds"]
    grid = data_["Grid"]
    codebook = data_["Codebook"]
else:
    raise Exception("User cancelled")

# Set grid
if grid.lower() == "matrix":
    KEYS = MATRIX_KEYS
elif grid.lower() == "qwerty":
    KEYS = QWERTY_KEYS
else:
    raise Exception("Unknown grid:", grid)

# Set codes
flat_keys = [key for row in KEYS for key in row]
n_keys = len(flat_keys)
if codebook.lower() == "shifted m-sequence":
    codes = np.load(os.path.join("codes", "shifted_m_sequence.npz"))["codes"]
    if grid.lower() == "matrix":
        codes = codes[::2, :]  # select the proper lags
elif codebook.lower() == "modulated gold codes":
    codes = np.load(os.path.join("codes", "modulated_gold_codes.npz"))["codes"]
else:
    raise Exception("Unknown codebook:", codebook)

# Setup speller (N.B.: starts the marker stream)
speller = Speller(
    size=SCREEN_SIZE,
    width=SCREEN_WIDTH,
    distance=SCREEN_DISTANCE,
    screen=SCREEN_ID,
    fr=SCREEN_FR,
    window_color=WINDOW_COLOR,
)
ppd = speller.get_pixels_per_degree()

# Set up and start LSL Recorder
try:
    print("Starting LSL recorder")
    recorder = LSLRecorder(app_root=LSL_RECORDER_APP_DIR)
    recorder.set_recorder(
        root=DATA_DIR, subject=subject, session=session, run=run, task=TASK
    )
    recorder.update()
    recorder.start()
except Exception as error:
    raise Exception(
        "Error in starting the LSL recorder. Did you start the LSL Recorder App?"
    )

# Log version information
speller.log(
    f"python_version;{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
)
speller.log(f"psychopy_version;{psychopy.__version__}")

# Log settings
speller.log(
    f"settings;subject={subject};age={age};sex={sex};"
    + f"screen_fr={SCREEN_FR};screen_distance={SCREEN_DISTANCE};"
    + f"cue_time={CUE_TIME};trial_time={TRIAL_TIME};iti_time={ITI_TIME};"
    + f"grid={grid.lower()};codebook={codebook.lower()}"
)

# Show instructions
speller.add_text_field(
    name="instructions",
    text="",
    size=SCREEN_SIZE,
    pos=(0, 0),
    field_color=(-1, -1, -1),
    text_color=(1, 1, 1),
    text_size=int(ppd),
    text_alignment="center",
)
instructions = (
    "You will be presented with a grid of symbols.\n"
    f"A target symbol will be highlighted in green for {CUE_TIME:.1f} s.\n"
    f"Then, all symbols, also the target, will flash for {TRIAL_TIME:.1f} s.\n"
    "During that flashing, keep fixating your eyes at the target symbol.\n"
    f"You will fixate at each of {n_keys} symbols once, in random order.\n"
    "During the entire task, do not move and minimize eye blinks.\n"
    f"This task takes about {n_keys * (CUE_TIME + TRIAL_TIME + ITI_TIME) / 60:.1f} min.\n"
)
speller.set_field_text(name="instructions", text=instructions)
speller.log("start_instructions", on_flip=True)
print("Presenting instructions")
# Ensure the instructions text is rendered to the screen before waiting for a key
speller.window.flip()
speller.wait_key()
speller.set_text_field_autodraw(name="instructions", autodraw=False)
speller.log("stop_instructions")

# Add keys
for y in range(len(KEYS)):
    for x in range(len(KEYS[y])):
        x_pos = int((x - len(KEYS[y]) / 2 + 0.5) * (KEY_WIDTH + KEY_SPACE) * ppd)
        y_pos = int(
            -(y - len(KEYS) / 2) * (KEY_HEIGHT + KEY_SPACE) * ppd
            - TEXT_FIELD_HEIGHT * ppd
        )
        if grid.lower() == "qwerty":
            if y == 0 or y == 1:
                x_pos += int(0.25 * KEY_WIDTH * ppd)
            elif y == 3 or y == 4:
                x_pos -= int(0.5 * KEY_WIDTH * ppd)
        images = [
            img_path
            for color in KEY_COLORS
            for img_path in STIMULI_DIR.glob(f"{color}/{KEYS[y][x]}_{color}*.png")
        ]
        speller.add_key(
            name=KEYS[y][x],
            images=images,
            size=(int(KEY_WIDTH * ppd), int(KEY_HEIGHT * ppd)),
            pos=(x_pos, y_pos),
        )

# Add text field at the top of the screen
x_pos = 0
y_pos = int(SCREEN_SIZE[1] / 2 - TEXT_FIELD_HEIGHT * ppd / 2)
speller.add_text_field(
    name="text",
    text="",
    size=(SCREEN_SIZE[0], int(TEXT_FIELD_HEIGHT * ppd)),
    pos=(x_pos, y_pos),
    field_color=(-1, -1, -1),
    text_color=(1, 1, 1),
)
speller.set_field_text(name="text", text="Preparing")


def _transform_binary(binary_list):
    result = []
    counter = 3
    current_value = 0

    for i, bit in enumerate(binary_list):
        if bit == 0:
            result.append(0)
            current_value = 0
        else:
            if current_value == 0:  # Rise event
                current_value = counter
                counter += 1
            result.append(current_value)
    return result


# Add stimuli
codes = np.repeat(
    codes, int(SCREEN_FR / PRESENTATION_RATE), axis=1
)  # upsample to frame refresh rate
stimuli = dict()
changing_stimuli = dict()
stimuli_to_keys = dict()
i = 0
for row in KEYS:
    for key in row:
        stimuli[key] = codes[i, :].tolist()
        changing_stimuli[key] = _transform_binary(stimuli[key])
        stimuli_to_keys[i] = key
        i += 1

# Set highlights
highlights = dict()
for row in KEYS:
    for key in row:
        highlights[key] = [0]

# Start
speller.log(marker="start_run")
speller.set_field_text(name="text", text="Starting")
print("Starting")
speller.run(highlights, duration=5.0)
speller.set_field_text(name="text", text="")

# Trial logic
lambda_list = [0.1, 0.15, 0.2, 0.3, 0.4]
contrast_list = [0.2, 0.4, 0.6, 0.8, 1.0]
color_list = [(100, 0, 0), (50, 0, 127), (50, 127, 0)]
conditions = data.createFactorialTrialList(
    {
        "lambda": lambda_list,
        "contrast": contrast_list,
        "color": color_list,
    }
)  # tuple list of unique trials


trials = data.TrialHandler(trialList=conditions, nReps=4, method="random")
rng = np.random.default_rng()
target_keys_sequence = np.random.choice(flat_keys, size=trials.nTotal, replace=True)
target_key_iter = iter(target_keys_sequence)
N_BLOCKS = 6
n_trials_per_block = 10  # trials.nTotal // N_BLOCKS

for this_trial in trials:
    # Only pause between blocks (skip before the very first trial)
    if trials.thisN > 0 and trials.thisN % n_trials_per_block == 0:
        block_num = trials.thisN // n_trials_per_block + 1
        speller.set_field_text(
            name="text",
            text=f"Block {block_num}/{N_BLOCKS}\n\nTake a short break, then press any key to continue.",
        )
        # Log the start of the break on the next flip so timestamps align with display
        speller.log(f"start_block;block={block_num}", on_flip=True)
        print(f"Starting block {block_num}/{N_BLOCKS}")
        # Ensure text is visible
        speller.window.flip()
        # Wait for any key to continue
        speller.wait_key(keyList=None)
        # Clear the text and send stop marker on flip
        speller.set_field_text(name="text", text="")
        speller.log(f"stop_block;block={block_num}", on_flip=True)
        speller.window.flip()

    proc = None
    current_lambda = this_trial["lambda"]
    current_contrast = this_trial["contrast"]
    lab_l, lab_a, lab_b = this_trial["color"]
    query_string = f"n_patches_actual==8"

    cmd = [
        sys.executable,  # Uses the current python interpreter
        "images/generate_fast.py",
        "render",
        "--query",
        query_string,  # Inject the random key here
        "--font_size_deg",
        "1",
        "--contrast",
        str(current_contrast),  # Inject contrast
        "--lambda_deg",
        str(current_lambda),  # Inject calculated lambda
        "--lab_l",
        str(lab_l),  # Inject L
        "--lab_a",
        str(lab_a),  # Inject A
        "--lab_b",
        str(lab_b),  # Inject B
        "--r_cutoff_deg",
        "0.3",
        "--gamma",
        "0.6",
    ]

    proc = subprocess.Popen(cmd)

    target_key = next(target_key_iter)
    # there is also trials.thisTrialN and trials.thisRepN
    trial_idx = trials.thisN + 1
    print(trials.thisTrial)
    trials.addData("target_key", target_key)
    print(f"{1 + trials.thisN:02d}/{trials.nTotal:d}\t{target_key:s}")

    # Cue
    highlights[target_key] = [1]
    out = speller.run(
        highlights,
        CUE_TIME,
        start_marker=f"start_cue;trial={trial_idx};key={target_key}",
        stop_marker=f"stop_cue;trial={trial_idx}",
    )
    highlights[target_key] = [0]
    if out > 0:
        break

    # Trial
    out = speller.run(
        changing_stimuli,
        TRIAL_TIME,
        start_marker=f"start_trial;trial={trial_idx}",
        stop_marker=f"stop_trial;trial={trial_idx}",
    )
    if out > 0:
        break

    # --- Inter-trial & Background Reloading ---
    reloaded = False

    if ITI_TIME > 0:
        n_iti_frames = int(ITI_TIME * speller.fr)

        # Send start marker
        speller.log(f"start_inter_trial;trial={trial_idx}", on_flip=True)

        for i in range(n_iti_frames):
            # 1. Flip window immediately
            # Since speller.run() sets autoDraw=True, this keeps the keys visible.
            speller.window.flip()

            # 2. Check background process
            # If generation is done and we haven't reloaded yet, do it now.
            if proc and not reloaded:
                if proc.poll() is not None:  # Check if process finished
                    proc.wait()  # Clean up process
                    speller.reload_keys()  # Reload textures
                    reloaded = True  # Mark as done

            # 3. Check Quit (every 60 frames)
            if i % 60 == 0 and speller.is_quit():
                recorder.stop()
                speller.quit()
                sys.exit()

        # Send stop marker
        speller.log(f"stop_inter_trial;trial={trial_idx}", on_flip=True)
        speller.window.flip()

    # --- Finalize Synchronization ---
    # If ITI was too short or skipped, ensure we finish reloading before the next trial
    if proc:
        proc.wait()
        if not reloaded:
            speller.reload_keys()


# Stop
speller.log(marker="stop_run")
speller.set_field_text(name="text", text="Stopping")
print("Stopping")
speller.run(highlights, duration=5.0)

# Stop LSL Recorder
recorder.stop()

# Stop speller
speller.quit()
