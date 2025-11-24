class State:
    def __init__(self, manager):
        self.manager = manager
        
    def update(self, dt):
        pass
        
    def draw(self, surface):
        pass
    
    def handle_event(self, event):
        pass
        
    def on_enter(self):
        pass
        
    def on_exit(self):
        pass

class StateManager:
    def __init__(self):
        self.stack = []
        
    def push(self, state):
        if self.stack:
            self.stack[-1].on_exit()
        self.stack.append(state)
        state.on_enter()
        
    def pop(self):
        if self.stack:
            self.stack[-1].on_exit()
            self.stack.pop()
        if self.stack:
            self.stack[-1].on_enter()
            
    def set(self, state):
        """Replaces the entire stack with a single state"""
        while self.stack:
            self.stack[-1].on_exit()
            self.stack.pop()
        self.stack.append(state)
        state.on_enter()
        
    def update(self, dt):
        if self.stack:
            self.stack[-1].update(dt)
            
    def draw(self, surface):
        if self.stack:
            self.stack[-1].draw(surface)
            
    def handle_event(self, event):
        if self.stack:
            self.stack[-1].handle_event(event)
