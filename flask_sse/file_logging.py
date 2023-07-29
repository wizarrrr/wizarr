from queue import Queue, Full
from flask import Response
from time import sleep
from threading import Thread

class MessageAnnouncer:

    def __init__(self, file_path):
        self.listeners = []
        self.file_path = file_path
        # Thread(target=self._listen).start()

    def listen(self):
        q = Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                listener: Queue = self.listeners[i]
                listener.put_nowait(msg)
            except Full:
                del self.listeners[i]

    def _listen(self):
        while True:
            with open(self.file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    self.announce(line)

    def response(self):
        def stream():
            messages = self.listen()
            while True:
                msg = messages.get()  # blocks until a new message arrives
                yield f"data: {msg}\n\n"

        return Response(stream(), mimetype='text/event-stream')
