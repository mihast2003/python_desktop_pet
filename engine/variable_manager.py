

class VariableManager:
    def __init__(self, config):
        self.values = {}
        self.rates = {}

        for name, cfg in config.items():
            self.values[name] = float(cfg.get("value", 0.0))
            self.rates[name] = float(cfg.get("rate", 0.0))

    def update(self, dt):
        for name, rate in self.rates.items():
            self.values[name] += rate * dt

    def get(self, name):
        return self.values.get(name, 0.0)

    def set(self, name, value):
        self.values[name] = float(value)

    def add(self, name, delta):
        self.values[name] += delta
        print(self.values[name], name)