from v3x_zulfiqar_gideon import ParchmentDisplay

class ObjectiveDisplay(ParchmentDisplay):
    """
    Objective display overlay using engine's ParchmentDisplay.
    Keeps same interface for game compatibility.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
