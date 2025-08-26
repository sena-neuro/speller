import os
import pyxdf


DATA_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "cvep")
SUBJECT = "01"
SESSION = "01"
RUN = "001"
TASK = "cvep"

reset_to_zero = True


fn = os.path.join(DATA_DIR, f"sub-{SUBJECT}", f"ses-{SESSION}", "eeg",
                  f"sub-{SUBJECT}_ses-{SESSION}_task-{TASK}_run-{RUN}_eeg.xdf")
streams = pyxdf.load_xdf(fn)[0]
names = [stream["info"]["name"][0] for stream in streams]
print("Available streams:", ", ".join(names))

marker_stream = streams[names.index("MarkerStream")]
if reset_to_zero:
    marker_stream["time_stamps"] -= marker_stream["time_stamps"][0]
for time_stamp, marker in zip(marker_stream["time_stamps"], marker_stream["time_series"]):
    print(f"{time_stamp}\t{marker[0]}")
