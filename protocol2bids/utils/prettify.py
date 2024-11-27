import json


class JSON(dict):

    def __str__(self):
        return json.dumps(self, indent=2)

    def __repr__(self) -> str:
        return self.__str__()


class JSONs(dict):

    def __str__(self):
        lines = []
        for key, value in self.items():
            lines.append(key)
            lines.append(json.dumps(value, indent=2))
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return self.__str__()
