from abc import ABC, abstractmethod


class BaseConfig(ABC):

    @staticmethod
    def factory(type):
        if type == 'ROCK64':
            return Rock64Config()
        raise ValueError("invalid config type ({}) given".format(type))

    @abstractmethod
    def get_pullupdown(self):
        pass

    @abstractmethod
    def get_highlow(self):
        pass




class Rock64Config(BaseConfig):

    def get_pullupdown(self):
        return 0, 1

    def get_highlow(self):
        return str(1), str(0)
