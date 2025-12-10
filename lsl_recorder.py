import os
import socket
import subprocess
import time
import platform
from pathlib import Path
from typing import Optional


def find_lsl_recorder_app() -> Optional[str]:
    """
    Automatically detect the LSL Recorder application path on the current platform.

    Returns
    -------
    str or None
        Path to the LabRecorder application, or None if not found.
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        possible_paths = [
            Path.home()
            / ".local"
            / "opt"
            / "labrecorder"
            / "LabRecorder"
            / "LabRecorder.app",
            Path("/opt/homebrew/Cellar/labrecorder")
            / "LabRecorder"
            / "LabRecorder.app",
            Path("/usr/local/opt/labrecorder/LabRecorder/LabRecorder.app"),
            Path.home() / "Applications" / "LabRecorder.app",
            Path("/Applications/LabRecorder.app"),
        ]
    elif system == "Windows":
        possible_paths = [
            Path.home() / "AppData" / "Local" / "LabRecorder" / "LabRecorder.exe",
            Path("C:\\") / "Program Files" / "LabRecorder" / "LabRecorder.exe",
            Path("C:\\") / "Program Files (x86)" / "LabRecorder" / "LabRecorder.exe",
        ]
    else:  # Linux
        possible_paths = [
            Path.home() / ".local" / "share" / "applications" / "LabRecorder",
            Path("/usr/local/bin/LabRecorder"),
            Path("/usr/bin/LabRecorder"),
        ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    return None


class LSLRecorder(object):
    """
    LSL Recorder controller for recording neural data.

    Parameters
    ----------
    address: str (default: "localhost")
        Address of the LSL Recorder App socket.
    port: int (default: 22345)
        Port of the LSL recorder App socket.
    app_root: str (default: None)
        Root of the LSL Recorder App. If None, will attempt auto-detection.
        Can also be set via the LSL_RECORDER_APP environment variable.
    auto_launch: bool (default: True)
        Whether to automatically launch the LSL Recorder App if not running.
    """

    def __init__(
        self,
        address: str = "localhost",
        port: int = 22345,
        app_root: Optional[str] = None,
        auto_launch: bool = True,
    ):
        self.address = address
        self.port = port
        self.system = platform.system()

        # Determine app path: explicit arg > environment variable > auto-detect
        if app_root is None:
            app_root = os.environ.get("LSL_RECORDER_APP")
        if app_root is None and auto_launch:
            app_root = find_lsl_recorder_app()

        # Launch LSL Recorder App if path was found
        if app_root is not None and auto_launch:
            self._launch_app(app_root)
            time.sleep(2)

        # Open socket
        self.socket = socket.create_connection((address, port))

    def _launch_app(self, app_root: str) -> None:
        """
        Launch the LSL Recorder application on the current platform.

        Parameters
        ----------
        app_root: str
            Path to the LSL Recorder application.
        """
        if not Path(app_root).exists():
            raise FileNotFoundError(f"LSL Recorder app not found at: {app_root}")

        try:
            if self.system == "Darwin":  # macOS
                subprocess.Popen(["open", app_root])
            elif self.system == "Windows":
                subprocess.Popen([app_root])
            else:  # Linux
                subprocess.Popen([app_root])
        except Exception as e:
            raise RuntimeError(f"Failed to launch LSL Recorder: {e}")

    def set_recorder(
            self,
            root: str,
            subject: str,
            session: str,
            run: int,
            task: str,
    ) -> int:
        """
        Data will be saved as root/sub-subject/ses-session/sub-subject_ses-session_run-run_task-task.xdf

        Parameters
        ----------
            root: str
                The data root to save the data to.
            subject: str
                The subject identifier.
            session: str
                The session identifier.
            run: int
                The run identifier.
            task: str
                The task identifier.
        Returns
        -------
            flag: int
                Whether run-time errors emerged
        """
        msg = (
            b"filename {root:%b} {task:%b} {run:%x} {participant:%b} {session:%b}\n"
            % (
                str(root).encode("utf8"),
                task.encode("utf8"),
                run,
                subject.encode("utf8"),
                session.encode("utf8"),
            )
        )
        self.socket.sendall(msg)
        time.sleep(1)
        return 0

    def update(
            self
    ) -> int:
        """
        Returns
        -------
            flag: int
                Whether run-time errors emerged
        """
        self.socket.sendall(b"update\n")
        time.sleep(2)
        return 0

    def start(
            self
    ) -> int:
        """
        Returns
        -------
            flag: int
                Whether run-time errors emerged
        """
        self.socket.sendall(b"start\n")
        time.sleep(5)
        return 0

    def stop(
            self
    ) -> int:
        """
        Returns
        -------
            flag: int
                Whether run-time errors emerged
        """
        self.socket.sendall(b"stop\n")
        time.sleep(5)
        return 0


if __name__ == "__main__":
    # Example usage - auto-detect and launch LSL Recorder
    # You can also set LSL_RECORDER_APP environment variable to specify a custom path
    print(f"Detected LSL Recorder at: {find_lsl_recorder_app()}")

    recorder = LSLRecorder()
    recorder.set_recorder(
        root=os.path.join(os.path.expanduser("~"), "Downloads", "test"),
        subject="02",
        session="03",
        run=4,
        task="test",
    )
    recorder.update()
    recorder.start()
    time.sleep(3)
    recorder.stop()
