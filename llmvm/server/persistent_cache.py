import os
from typing import Dict, Generic, Iterable, TypeVar

import dill

K = TypeVar('K')
V = TypeVar('V')

class MemoryCache(Generic[K, V]):
    def __init__(self):
        self.cache: Dict[K, V] = {}

    def get(self, key: K) -> V | None:
        return self.cache.get(key)

    def set(self, key: K, value: V) -> None:
        self.cache[key] = value

    def setup(self) -> None:
        pass

    def delete(self, key: K) -> None:
        self.cache.pop(key, None)

    def has_key(self, key: K) -> bool:
        return key in self.cache

    def keys(self) -> Iterable[K]:
        return self.cache.keys()


class PersistentCache:
    # todo needs to be completely replaced.
    def __init__(self, filename: str):
        self.filename = filename
        self.cache = {}

        if not os.path.isfile(self.filename):
            with open(self.filename, 'wb') as f:
                dill.dump({}, f)

    def _serialize_key(self, key):
        return dill.dumps(key)

    def _deserialize_key(self, serialized_key):
        return dill.loads(serialized_key)

    def setup(self):
        if not os.path.isfile(self.filename):
            with open(self.filename, 'wb') as f:
                dill.dump({}, f)

        if not self.cache:
            with open(self.filename, 'rb') as f:
                self.cache = dill.load(f)

    def set(self, key, value):
        self.setup()
        serialized_key = self._serialize_key(key)

        self.cache[serialized_key] = value

        with open(self.filename, 'rb+') as f:
            dill.dump(self.cache, f)

    def get(self, key):
        self.setup()
        return self.cache.get(self._serialize_key(key))

    def delete(self, key):
        self.setup()
        with open(self.filename, 'rb+') as f:
            self.cache = dill.load(f)
            serialized_key = self._serialize_key(key)
            if serialized_key in self.cache:
                del self.cache[serialized_key]
                f.seek(0)
                dill.dump(self.cache, f)

    def has_key(self, key):
        self.setup()
        return self._serialize_key(key) in self.cache

    def keys(self):
        self.setup()
        return [self._deserialize_key(k) for k in self.cache.keys()]

    def gen_key(self):
        keys = self.keys()
        return keys[-1] + 1 if keys else 1
