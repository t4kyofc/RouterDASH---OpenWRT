# Minimal blinker compatibility fallback for stripped OpenWrt Python environments.
class _Signal:
    def __init__(self, name=None): self.name=name; self._subs=[]
    def connect(self, receiver, sender=None, weak=True): self._subs.append(receiver); return receiver
    def disconnect(self, receiver, sender=None):
        try: self._subs.remove(receiver)
        except ValueError: pass
    def send(self, sender=None, **kwargs):
        out=[]
        for fn in list(self._subs):
            try: out.append((fn, fn(sender, **kwargs)))
            except TypeError: out.append((fn, fn(**kwargs)))
        return out
class Namespace:
    def __init__(self): self._signals={}
    def signal(self, name, doc=None):
        return self._signals.setdefault(name, _Signal(name))
def signal(name, doc=None):
    return _default_namespace.signal(name, doc)
_default_namespace = Namespace()
