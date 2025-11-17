# Minimal c-VEP Speller

This repository contains the documentation and resources to set up a minimal c-VEP speller BCI for communication using Psychopy. This implementation uses PsychoPy's ImageStim with pre-rendered images to boost speed while having a larger burden on memory. See the speller2 repository for an implementation using PsychoPy's TextBox2 for more continuous stimulation.

## Setup
Use a simple terminal/cmd to go through the following steps.

1. Make a [conda](https://www.anaconda.com/download) environment with Python 3.10 (not higher, as PsychoPy needs 3.10) as follows:

```bash
conda create --name cvep python=3.10.18
```

2. Activate the `cvep` conda environment as follows:

```bash
conda activate cvep
```

3. Install all the requirements as follows:

```bash
pip install -r requirements.txt
```

4. Install the [LSL Recorder App](https://github.com/labstreaminglayer/App-LabRecorder).

## Run
Use a simple terminal/cmd to go through the following steps.

1. Make sure that the LSL Recorder App is open in the background. Starting and stopping of recording will be done automatically.

2. Activate the `cvep` conda environment as follows:

```bash
conda activate cvep
```

3. Start the speller as follows:
```bash
python experiment.py
```

4. A dialog box will appear in which one can fill out session information. Fill out as required and press OK.
5. Task instructions will be presented. Read carefully and press the key `c` to continue.
6. The speller will start and randomly go through all symbols, first cueing the target symbol in green and then presenting visual stimulation. The participant should fixate their eyes on the cued symbol, and keep their eyes fixated during the visual stimulation period. Additionally, overall, the participant should not move and minimize eye blinks.
7. After all symbols were presented once, the speller will stop and close.
8. Please note, that during the runtime one can abort the speller by pressing the key `q` or `escape`. The speller will then close immediately.