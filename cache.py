from collections import OrderedDict
from collections.abc import Hashable, Iterable, Sized, Mapping

import redis
import ujson

r = redis.StrictRedis(host='localhost', port=6379, db=0)

_hgetall = r.register_script(
    """
    local hgetall = function (key)
      local data = redis.call('HGETALL', key)
      local hash = {}

      for idx = 1, #data, 2 do
        hash[data[idx]] = cjson.decode(data[idx + 1])
      end

      return hash
    end

    local hashes = {}

    for i=1, #KEYS do
      hashes[i] = hgetall(KEYS[i])
    end

    return cjson.encode(hashes)
    """
)


def dumps(obj):
    return ujson.dumps(obj)


def loads(s):
    return ujson.loads(s)


def get(key):
    return loads(r.get(key))


def set(key, value=None):
    if type(key) is dict:
        for k, v in key.items():
            r.set(k, dumps(v))
    else:
        return r.set(key, dumps(value))


def hget(key, field):
    return loads(r.hget(key, field))


def hgetall(key):
    if type(key) is str:
        return {k.decode(): loads(v) for k, v in r.hgetall(key).items()}
    else:
        return loads(_hgetall(keys=key))


def hset(key, value):
    if len(value) == 1:
        k, v = tuple(value.items())[0]
        return r.hset(key, k, dumps(v))
    else:
        return r.hmset(key, {k: dumps(v) for k, v in value.items()})


def hkeys(key):
    return (f.decode() for f in r.hkeys(key))


def sadd(*args, **kwargs):
    return r.sadd(*args, **kwargs)


def smembers(key):
    return (m.decode() for m in r.smembers(key))


def srandmember(*args, **kwargs):
    members = r.srandmember(*args, **kwargs)
    if type(members) is list:
        return [member.decode() for member in members]
    else:
        return members.decode()


class Hash(Hashable, Mapping):
    def __init__(self, key):
        self.key = key

    def __hash__(self):
        return hash(self.key)

    def __getitem__(self, field):
        return hget(self.key, field)

    def __contains__(self, field):
        return r.hexists(self.key, field)

    def __iter__(self):
        yield from hkeys(self.key)

    def __len__(self):
        return r.hlen(self.key)

    def todict(self):
        return hgetall(self.key)


class Hashes(Iterable, Sized):
    """This class enables buffered iteration over a list of hashes.
    The hashes are returned as regular dicts."""
    def __init__(self, hashes, bufsize=100):
        self.keys = tuple(h.key for h in hashes)
        self.bufsize = bufsize

    def __iter__(self):
        i = 0
        while i < len(self.keys):
            results = hgetall(self.keys[i:i + self.bufsize])
            i += self.bufsize
            yield from results

    def __len__(self):
        return len(self.keys)


class HashSet(Mapping):
    def __init__(self, key, tokey, sortkey=None):
        self.key = key
        self.tokey = tokey
        self.sortkey = sortkey

    def __getitem__(self, member):
        return Hash(self.tokey(member))

    def __contains__(self, member):
        return r.sismember(self.key, member)

    def __iter__(self):
        if self.sortkey:
            yield from sorted(smembers(self.key), key=self.sortkey)
        else:
            yield from smembers(self.key)

    def __len__(self):
        return r.scard(self.key)


class SearchHashSet(HashSet):
    """This class optimizes search on a set of hashes by first obtaining
    and storing all the fields necessary for search, allowing faster access
    to them. Other fields are accessed as required from the cache."""
    class SearchHash(Hash):
        def __init__(self, key, member, set_):
            super().__init__(key)
            self.member = member
            self.set_ = set_

        def __getitem__(self, field):
            if field in self.set_.fields:
                return self.set_._gethashfield(self, field)
            else:
                return super().__getitem__(field)

    def __init__(self, key, tokey, fields, sortkey=None):
        super().__init__(key, tokey)
        self.fields = fields

        get = ('#',) + tuple('{}->{}'.format(tokey('*'), f) for f in fields)
        self.result = r.sort(key, get=get)

        hashes = []
        for i in range(0, len(self.result), len(fields) + 1):
            hashes.append((self.result[i].decode(), i + 1))

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
