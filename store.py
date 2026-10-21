from collections import OrderedDict
from collections.abc import AsyncIterator, Hashable, Sized, Mapping

import fastsimdjson
from valkey.asyncio.client import Pipeline as _Pipeline, Valkey as _Valkey


def dumps(obj):
    return fastsimdjson.dumpb(obj)


def mdumps(d):
    return {k: dumps(v) for k, v in d.items()}


def loads(s):
    if s is not None:
        return fastsimdjson.loads(s)


class Valkey(_Valkey):
    async def get(self, *args, **kwargs):
        return loads(await super().get(*args, **kwargs))

    def set(self, key, value):
        return super().set(key, dumps(value))

    def setex(self, key, time, value):
        return super().setex(key, time, dumps(value))

    def mset(self, map_):
        return super().mset(mdumps(map_))

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
            dumps(value) if value is not None else None,
            mdumps(mapping) if mapping is not None else None
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

    def Hash(self, *args, **kwargs):
        return Hash(self, *args, **kwargs)

    def Hashes(self, *args, **kwargs):
        return Hashes(self, *args, **kwargs)

    def HashSet(self, *args, **kwargs):
        return HashSet(self, *args, **kwargs)

    async def SearchHashSet(self, *args, **kwargs):
        return await SearchHashSet.create(self, *args, **kwargs)


class Pipeline(_Pipeline, Valkey):
    pass


class Hash(Hashable, Mapping):
    def __init__(self, valkey, key):
        self.v = valkey
        self.key = key

    def __hash__(self):
        return hash(self.key)

    async def __getitem__(self, field):
        return await self.v.hget(self.key, field)

    async def contains(self, field):
        return await self.v.hexists(self.key, field)

    async def __iter__(self):
        return await self.v.hkeys(self.key)

    async def __len__(self):
        return await self.v.hlen(self.key)

    async def todict(self):
        return await self.v.hgetall(self.key)


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


class HashSet(Mapping):
    def __init__(self, valkey: Valkey, key, tokey, sortkey=None):
        self.v = valkey
        self.key = key
        self.tokey = tokey
        self.sortkey = sortkey

    def __getitem__(self, member):
        return Hash(self.v, self.tokey(member))

    async def __contains__(self, member):
        return await self.v.sismember(self.key, member)

    async def __iter__(self):
        if self.sortkey:
            return sorted(await self.v.smembers(self.key), key=self.sortkey)
        else:
            return await self.v.smembers(self.key)

    async def __len__(self):
        return await self.v.scard(self.key)


class SearchHashSet(HashSet):
    """This class optimizes search on a set of hashes by first obtaining
    and storing all the fields necessary for search, allowing faster access
    to them. Other fields are accessed as required from the store."""
    class SearchHash(Hash):
        def __init__(self, key, index, set_):
            super().__init__(set_.v, key)
            self.index = index
            self.set_ = set_

        def __getitem__(self, field):
            if field in self.set_.fields:
                return self.set_._gethashfield(self, field)
            else:
                return super().__getitem__(field)

    @classmethod
    async def create(cls, valkey, key, tokey, fields, sortkey=None):
        self = cls(valkey, key, tokey)
        self.fields = {f: (i+1) for i, f in enumerate(fields)}

        get = ('#',) + tuple('{}->{}'.format(tokey('*'), f) for f in fields)
        self.result = [
            int(v) if i % (len(fields)+1) == 0 else loads(v)
            for i, v in enumerate(await self.v.sort(key, by='nosort', get=get))
        ]

        hashes = []
        for i in range(0, len(self.result), len(fields) + 1):
            member = self.result[i]
            hashes.append((member,
                           self.SearchHash(self.tokey(member), i, self)))

        if sortkey:
            hashes.sort(key=lambda k: sortkey(k[0]))
            self.hashes = OrderedDict(hashes)
        else:
            self.hashes = dict(hashes)

        return self

    def __getitem__(self, member):
        return self.hashes[member]

    def __contains__(self, member):
        return member in self.hashes

    def __iter__(self):
        return iter(self.hashes)

    def __len__(self):
        return len(self.hashes)

    def _gethashfield(self, hash_, field):
        return self.result[hash_.index + self.fields[field]]
