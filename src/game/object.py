class Position:
    def __init__(self, x : int, y : int):
        self.x = x
        self.y = y
    
class GameObject:
    def __init__(self, name : str, id :int):
        self.name = name

    def __str__(self):
        return self.name

