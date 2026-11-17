# ABOUTME: Remembers the hole openings read for the dialog's current selection, so changing a
# ABOUTME: setting plans the seats again without reading the model again.


class OpeningsCache:
    """The openings read for the last selection, so changing a setting does not read the model again."""

    def __init__(self, read_openings):
        self.read_openings = read_openings
        self.clear()

    def clear(self):
        self.rims = None
        self.result = None

    def read(self, design, rims):
        if not self.matches(rims):
            result = self.read_openings(design, rims)
            self.rims, self.result = rims, result
        return self.result

    def matches(self, rims):
        return (self.rims is not None and len(rims) == len(self.rims)
                and all(rim == cached for rim, cached in zip(rims, self.rims)))
