# Minimal c-VEP Speller

This repository contains the documentation and resources to set up a minimal c-VEP speller BCI for communication using Psychopy. 

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

## Run
Use a simple terminal/cmd to go through the following steps.

1. Activate the `cvep` conda environment as follows:

```bash
conda activate cvep
```

2. Start the c-VEP speller BCI as follows:
```bash
python speller.py
```

3. A dialog box will appear in which one can fill out participant information as well as change certain settings of the speller. Fill out as required and press OK. 

4. The c-VEP Speller BCI will emerge and initially wait for a buttonpress to start. Press the key `c` to continue.

5. The c-VEP Speller BCI will randomly go through all symbols, first cueing in green which symbol is the current target and then presenting visual stimulation. The participant should fixate their eyes on the cued symbol, and keep their eyes fixated during the visual stimulation period. Additionally, overall, the participant should not move and minimize eye blinks. 

6. After all symbols were presented once, the c-VEP BCI Speller will stop and wait for a key press. Press the key `c` to continue. The speller will close.

7. Please note, that during the runtime one can abort the c-VEP Speller BCI by pressing the key `q` or `escape`. The speller will then close immediately.