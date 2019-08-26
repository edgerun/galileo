from typing import NamedTuple


class AppInfo(NamedTuple):
    name: str
    manifest: dict
    archive_path: str = None


class Context:
    name: str
    path: str
    manifest: dict
    parameters: dict

    def __str__(self) -> str:
        return 'Context%s' % self.__dict__

    def __repr__(self):
        return self.__str__()
