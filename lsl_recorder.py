import os
import socket
import time


class LSLRecorder(object):

    def __init__(self, address="localhost", port=22345):
        self.socket = socket.create_connection((address, port))

    def set_recorder(self, root, subject, session, run, task):
        self.update()
        time.sleep(2)
        msg = f"filename {{root:{root}}} {{participant:{subject}}} {{session:{session}}} {{run:{run}}} {{task:{task}}}\n"
        self.socket.sendall(msg.encode("UTF-8"))
        time.sleep(1)
        return 0

    def update(self):
        self.socket.sendall(b"update\n")
        return 0

    def start(self):
        self.socket.sendall(b"start\n")
        time.sleep(5)
        return 0

    def stop(self):
        self.socket.sendall(b"stop\n")
        time.sleep(5)
        return 0


if __name__ == "__main__":
    recorder = LSLRecorder()
    recorder.set_recorder(
        root=os.path.join(os.path.expanduser("~"), "Downloads", "test"),
        subject="03",
        session="05",
        run="03",
        task="test",
    )
    recorder.update()
    recorder.start()
    time.sleep(3)
    recorder.stop()
