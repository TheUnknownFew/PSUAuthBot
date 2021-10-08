from pydantic import BaseModel


class MyModel(BaseModel):
    _a: int
    b: int

    def set_a(self):
        self.__a = 5


def start():
    myModel = MyModel.parse_obj({'b': 1})
    print(myModel)


if __name__ == '__main__':
    start()
