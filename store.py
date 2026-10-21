from collections.abc import AsyncIterator, Hashable, Sized, Mapping

import fastsimdjson
from valkey.asyncio.client import Pipeline as _Pipeline, Valkey as _Valkey


def dumpb(obj):
    return fastsimdjson.dumpb(obj)


def mdumpb(d):
    return {k: dumpb(v) for k, v in d.items()}


def loads(s):
    if s is not None:
        return fastsimdjson.loads(s)


class Valkey(_Valkey):
    async def get(self, *args, **kwargs):
        return loads(await super().get(*args, **kwargs))

    def set(self, key, value):
        return super().set(key, dumpb(value))

    def setex(self, key, time, value):
        return super().setex(key, time, dumpb(value))

    def mset(self, map_):
        return super().mset(mdumpb(map_))

    async def hget(self, *args, **kwargs):
        return loads(await super().hget(*args, **kwargs))

    async def hgetall(self, key):
        self._hgetall = getattr(
            self, '_hgetall',
            self.register_script(
                """
                local hgetall = function (key)
                  local data = server.call('HGETALL', key)
                  local hash = {}

                  for i = 1, #data, 2 do
                    hash[data[i]] = cjson.decode(data[i + 1])
                  end

                  return hash
                end

                local hashes = {}

                for i = 1, #KEYS do
                  hashes[i] = hgetall(KEYS[i])
                end

                return cjson.encode(hashes)
                """
            )
        )
        if type(key) is str:
            return {k.decode(): loads(v)
                    for k, v in (await super().hgetall(key)).items()}
        else:
            return loads(await self._hgetall(key))

    def hset(self, name, key=None, value=None, mapping=None):
        return super().hset(
            name, key,
            dumpb(value) if value is not None else None,
            mdumpb(mapping) if mapping is not None else None
        )

    async def hkeys(self, *args, **kwargs):
        return (f.decode() for f in await super().hkeys(*args, **kwargs))

    async def smembers(self, *args, **kwargs):
        return (m.decode() for m in await super().smembers(*args, **kwargs))

    async def srandmember(self, *args, **kwargs):
        members = await super().srandmember(*args, **kwargs)
        if type(members) is list:
            return [member.decode() for member in members]
        else:
            return members.decode()

    async def lrange(self, *args, **kwargs):
        return (e.decode() for e in await super().lrange(*args, **kwargs))

    async def delete_all(self, match, count=100):
        cursor = None
        while cursor != 0:
            if cursor is None:
                cursor = 0
            cursor, keys = await self.scan(cursor, match, count)
            if keys:
                await self.delete(*keys)

    def pipeline(self, transaction=True, shard_hint=None):
        return Pipeline(
            self.connection_pool, self.response_callbacks, transaction,
            shard_hint
        )

    def Hashes(self, *args, **kwargs):
        return Hashes(self, *args, **kwargs)

    async def SearchHashSet(self, *args, **kwargs):
        return await SearchHashSet.create(self, *args, **kwargs)


class Pipeline(_Pipeline, Valkey):
    pass


class Hashes(AsyncIterator, Sized):
    """This class enables buffered iteration over a list of hashes.
    The hashes are returned as regular dicts."""
    def __init__(self, valkey, keys, bufsize=100):
        self.v = valkey
        self.keys = keys
        self.bufsize = bufsize
        self.i = -1

    def __aiter__(self):
        return self

    async def __anext__(self):
        self.i += 1
        if self.i >= len(self.keys):
            raise StopAsyncIteration
        if self.i % self.bufsize == 0:
            self.results = await self.v.hgetall(
                self.keys[self.i:self.i + self.bufsize]
            )
        return self.results[self.i % self.bufsize]

    def __len__(self):
        return len(self.keys)


class SearchHashSet(Mapping):
    """This class optimizes search on a set of hashes by first obtaining
    and storing all the fields necessary for search."""
    class SearchHash(Hashable, Mapping):
        def __init__(self, key, index, set_):
            self.key = key
            self.index = index
            self.set_ = set_

        def __hash__(self):
            return hash(self.key)

        def __iter__(self):
            return iter(self.set_.fields)

        def __len__(self):
            return len(self.set_.fields)

        def __getitem__(self, field):
            return self.set_._getvalue(self.index, field)

    @classmethod
    async def create(cls, valkey, *args, **kwargs):
        self = cls(*args, **kwargs)

        get = ('#',) + tuple(
            '{}->{}'.format(self.tokey('*'), f) for f in self.fields
        )

        self.result = [
            int(v) if i % (len(self.fields)+1) == 0 else loads(v)
            for i, v in enumerate(await valkey.sort(self.key, get=get))
        ]

        for i in range(0, len(self.result), len(self.fields) + 1):
            member = self.result[i]
            self.hashes[member] = self.SearchHash(self.tokey(member), i, self)

        return self

    def __init__(self, key, tokey, fields):
        self.key = key
        self.tokey = tokey
        self.fields = {f: (i+1) for i, f in enumerate(fields)}
        self.hashes = {}
        self.result = []

    def __getitem__(self, member):
        return self.hashes[member]

    def __contains__(self, member):
        return member in self.hashes

    def __iter__(self):
        return iter(self.hashes)

    def __len__(self):
        return len(self.hashes)

    def _getvalue(self, index, field):
        return self.result[index + self.fields[field]]
