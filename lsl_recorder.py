import os
import socket
import subprocess
import time


class LSLRecorder(object):
    """
    Parameters
    ----------
    address: str (default: "localhost")
        Address of the LSL Recorder App socket.
    port: int (default: 22345)
        Port of the LSL recorder App socket.
    app_root: str (default: None)
        Root of the LSL Recorder App.
    """
    def __init__(
            self,
            address: str = "localhost",
            port: int = 22345,
            app_root:str = None,
    ):
        # Spawn LSL Recorder App
        if app_root is not None:
            os.system(f"open {app_root}")
            time.sleep(2)

        # Open socket
        self.socket = socket.create_connection((address, port))

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
                root.encode("utf8"),
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
