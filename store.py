from collections import OrderedDict
from collections.abc import Hashable, Iterable, Sized, Mapping

import ujson
from redis import StrictRedis


def dumps(obj):
    return ujson.dumps(obj)


def mdumps(d):
    return {k: dumps(v) for k, v in d.items()}


def loads(s):
    if s is not None:
        return ujson.loads(s)


class Redis(StrictRedis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hgetall = self.register_script(
            """
            local hgetall = function (key)
              local data = redis.call('HGETALL', key)
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

    def get(self, *args, **kwargs):
        return loads(super().get(*args, **kwargs))

    def set(self, key, value):
        return super().set(key, dumps(value))

    def setex(self, key, time, value):
        return super().setex(key, time, dumps(value))

    def mset(self, map_):
        return super().mset(mdumps(map_))

    def hget(self, *args, **kwargs):
        return loads(super().hget(*args, **kwargs))

    def hgetall(self, key):
        if type(key) is str:
            return {k.decode(): loads(v)
                    for k, v in super().hgetall(key).items()}
        else:
            return loads(self._hgetall(keys=key))

    def hset(self, key, field, value):
        return super().hset(key, field, dumps(value))

    def hmset(self, key, map_):
        return super().hmset(key, mdumps(map_))

    def hkeys(self, *args, **kwargs):
        return (f.decode() for f in super().hkeys(*args, **kwargs))

    def smembers(self, *args, **kwargs):
        return (m.decode() for m in super().smembers(*args, **kwargs))

    def srandmember(self, *args, **kwargs):
        members = super().srandmember(*args, **kwargs)
        if type(members) is list:
            return [member.decode() for member in members]
        else:
            return members.decode()

    def lrange(self, *args, **kwargs):
        return (e.decode() for e in super().lrange(*args, **kwargs))

    def sort(self, *args, **kwargs):
        result = super().sort(*args, **kwargs)
        if type(result) is int:
            return result
        else:
            return (x.decode() for x in result)

    def delete_all(self, match, count=100):
        cursor = None
        while cursor != 0:
            if cursor is None:
                cursor = 0
            cursor, keys = self.scan(cursor, match, count)
            if keys:
                self.delete(*keys)

    def Hash(self, *args, **kwargs):
        return Hash(self, *args, **kwargs)

    def Hashes(self, *args, **kwargs):
        return Hashes(self, *args, **kwargs)

    def HashSet(self, *args, **kwargs):
        return HashSet(self, *args, **kwargs)

    def SearchHashSet(self, *args, **kwargs):
        return SearchHashSet(self, *args, **kwargs)


class Hash(Hashable, Mapping):
    def __init__(self, redis, key):
        self.r = redis
        self.key = key

    def __hash__(self):
        return hash(self.key)

    def __getitem__(self, field):
        return self.r.hget(self.key, field)

    def __contains__(self, field):
        return self.r.hexists(self.key, field)

    def __iter__(self):
        yield from self.r.hkeys(self.key)

    def __len__(self):
        return self.r.hlen(self.key)

    def todict(self):
        return self.r.hgetall(self.key)


class Hashes(Iterable, Sized):
    """This class enables buffered iteration over a list of hashes.
    The hashes are returned as regular dicts."""
    def __init__(self, redis, keys, bufsize=100):
        self.r = redis
        self.keys = keys
        self.bufsize = bufsize

    def __iter__(self):
        i = 0
        while i < len(self.keys):
            results = self.r.hgetall(self.keys[i:i + self.bufsize])
            i += self.bufsize
            yield from results

    def __len__(self):
        return len(self.keys)


class HashSet(Mapping):
    def __init__(self, redis, key, tokey, sortkey=None):
        self.r = redis
        self.key = key
        self.tokey = tokey
        self.sortkey = sortkey

    def __getitem__(self, member):
        return Hash(self.r, self.tokey(member))

    def __contains__(self, member):
        return self.r.sismember(self.key, member)

    def __iter__(self):
        if self.sortkey:
            yield from sorted(self.r.smembers(self.key), key=self.sortkey)
        else:
            yield from self.r.smembers(self.key)

    def __len__(self):
        return self.r.scard(self.key)


class SearchHashSet(HashSet):
    """This class optimizes search on a set of hashes by first obtaining
    and storing all the fields necessary for search, allowing faster access
    to them. Other fields are accessed as required from the store."""
    class SearchHash(Hash):
        def __init__(self, key, member, set_):
            super().__init__(set_.r, key)
            self.member = member
            self.set_ = set_

        def __getitem__(self, field):
            if field in self.set_.fields:
                return self.set_._gethashfield(self, field)
            else:
                return super().__getitem__(field)

    def __init__(self, redis, key, tokey, fields, sortkey=None):
        super().__init__(redis, key, tokey)
        self.fields = fields

        get = ('#',) + tuple('{}->{}'.format(tokey('*'), f) for f in fields)
        self.result = tuple(self.r.sort(key, get=get))

        hashes = []
        for i in range(0, len(self.result), len(fields) + 1):
            hashes.append((self.result[i], i + 1))

        if sortkey:
            hashes.sort(key=lambda k: sortkey(k[0]))
            self.hashes = OrderedDict(hashes)
        else:
            self.hashes = dict(hashes)

    def __getitem__(self, member):
        return self.SearchHash(self.tokey(member), str(member), self)

    def __contains__(self, member):
        return str(member) in self.hashes

    def __iter__(self):
        yield from self.hashes

    def __len__(self):
        return len(self.hashes)

    def _gethashfield(self, hash_, field):
        i = self.hashes[hash_.member] + self.fields.index(field)
        return loads(self.result[i])
