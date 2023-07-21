"""
Server-Sent Events (SSE) for Flask applications.
Built by Ashley Bailey for Wizarr
"""

from os import urandom
from queue import Full, Queue
from re import search

from flask import Response


class MessageAnnouncer:
    """
    A class that allows listeners to register and receive messages.
    """

    def __init__(self):
        """
        Initializes an empty list of listeners.
        """
        self.listeners = []

    def listen(self):
        """
        Creates a new Queue object with a maximum size of 5 and appends it to the list of listeners.
        Returns the new Queue object.
        """
        q = Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        """
        Iterates over the list of listeners in reverse order.
        For each listener, attempts to put the message into the listener's queue using the put_nowait method.
        If the queue is full, the listener is removed from the list.
        If the listener's queue has been closed, it is also removed from the list.
        """
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except Full:
                # If the queue is full, remove the listener from the list
                del self.listeners[i]
            except AttributeError:
                # If the listener's queue has been closed, remove the listener from the list
                del self.listeners[i]


class ServerSentEvents:
    """
    A class that manages Server-Sent Events (SSE) for Flask applications.
    """

    def __init__(self):
        """
        Initializes an empty dictionary of announcers.
        """
        self.announcers = {}

    def announcer(self, id):
        """
        Returns the MessageAnnouncer object associated with the given ID.
        If the ID does not exist in the dictionary of announcers, creates a new MessageAnnouncer object and adds it to the dictionary.
        """
        if id not in self.announcers:
            self.announcers[id] = MessageAnnouncer()
        return self.announcers[id]
    
    def publish(self, msg):
        """
        Sends the given message to all announcers.
        """
        for id in self.announcers:
            self.send(msg, id)
    
    def create_announcer(self):
        """
        Creates a new announcer with a random ID and adds it to the dictionary of announcers.
        Returns the ID of the new announcer.
        """
        random_id = urandom(16).hex()
        self.announcers[random_id] = MessageAnnouncer()
        return random_id
    
    def delete_announcer(self, id):
        """
        Deletes the announcer with the given ID from the dictionary of announcers.
        """
        try:
            del self.announcers[id]
        except KeyError:
            print("Could not delete announcer with id", id)
            
    def response(self, id=None):
        """
        Returns a Flask Response object that streams SSE messages from the announcer with the given ID.
        """
        def stream():
            has_finished = False
            
            if id == None or id not in self.announcers:
                print("Could not find announcer with id", id)
                return

            q = self.announcer(id).listen()

            while has_finished == False:
                try:
                    msg = q.get()
                    yield msg
                except GeneratorExit:
                    has_finished = True
                    self.delete_announcer(id)
                except AttributeError:
                    has_finished = True
                    self.delete_announcer(id)
                except KeyboardInterrupt:
                    has_finished = True
                    self.delete_announcer(id)
                except Exception as e:
                    print(e)
                    has_finished = True
                    self.delete_announcer(id)
                    
                if search("event: end", msg) or search("event: error", msg):
                    has_finished = True
                    
        return Response(stream(), mimetype="text/event-stream")
    
    def send(self, msg_str, id, event="data"):
        """
        Sends the given message to the announcer with the given ID.
        """
        msg_id = len(self.announcer(id).listeners)
        msg = f"id: {msg_id}\nevent: {event}\ndata: {msg_str}\n\n"

        self.announcer(id).announce(msg)

        return self
    