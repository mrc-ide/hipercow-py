class AnyInstanceOf:
    def __init__(self, cls):
        self.cls = cls

    def __eq__(self, other):
        return isinstance(other, self.cls)

    def __ne__(self, other):
        return not isinstance(other, self.cls)

    def __repr__(self):
        return f"<ANY {self.cls.__name__}>"

    def __hash__(self):
        return hash(self.cls)
