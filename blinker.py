"""Minimal local fallback for environments without the python3-blinker package.

This file is intentionally tiny and only implements the subset Flask needs to
import and use signals safely on OpenWrt builds where the blinker package is
not available.
"""

from contextlib import contextmanager

ANY = object()


class Signal:
    def __init__(self, name=None, doc=None):
        self.name = name
        self.__doc__ = doc
        self._receivers = []

    def connect(self, receiver, sender=ANY, weak=True):
        self._receivers.append((receiver, sender))
        return receiver

    def connect_via(self, sender):
        def decorator(receiver):
            self.connect(receiver, sender=sender)
            return receiver
        return decorator

    def disconnect(self, receiver, sender=ANY):
        kept = []
        removed = False
        for current_receiver, current_sender in self._receivers:
            if current_receiver is receiver and (sender is ANY or current_sender is sender):
                removed = True
                continue
            kept.append((current_receiver, current_sender))
        self._receivers = kept
        return removed

    def has_receivers_for(self, sender):
        return any(current_sender is ANY or current_sender is sender for _, current_sender in self._receivers)

    def receivers_for(self, sender):
        for receiver, current_sender in list(self._receivers):
            if current_sender is ANY or current_sender is sender:
                yield receiver

    def send(self, sender=None, **kwargs):
        kwargs.pop("_async_wrapper", None)
        result = []
        for receiver in list(self.receivers_for(sender)):
            result.append((receiver, receiver(sender, **kwargs)))
        return result

    @contextmanager
    def connected_to(self, receiver, sender=ANY):
        self.connect(receiver, sender=sender)
        try:
            yield self
        finally:
            self.disconnect(receiver, sender=sender)

    temporarily_connected_to = connected_to

    @contextmanager
    def muted(self):
        yield self


class NamedSignal(Signal):
    pass


class Namespace(dict):
    def signal(self, name, doc=None):
        if name not in self:
            self[name] = NamedSignal(name, doc)
        return self[name]


default_namespace = Namespace()


def signal(name, doc=None):
    return default_namespace.signal(name, doc)
