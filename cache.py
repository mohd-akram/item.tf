import pickle
from collections import OrderedDict
from collections.abc import Mapping

import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)


def dumps(obj):
    return pickle.dumps(obj)


def loads(s):
    return pickle.loads(s)


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
    return {k.decode(): loads(v) for k, v in r.hgetall(key).items()}


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


class Hash(Mapping):
    def __init__(self, key):
        self.key = key

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
    class SearchHash(Hash):
        def __init__(self, key, cache):
            super().__init__(key)
            self.cache = cache

        def __getitem__(self, field):
            if field in self.cache:
                return self.cache[field]
            else:
                return super().__getitem__(field)

    def __init__(self, key, tokey, fields, sortkey=None):
        super().__init__(key, tokey, sortkey)
        self.fields = fields

        get = ('#',) + tuple('{}->{}'.format(tokey('*'), f) for f in fields)
        self.result = r.sort(key, get=get)

        hashes = []
        for i in range(0, len(self.result), len(fields)+1):
            hashes.append((self.result[i].decode(), i + 1))

        if sortkey:
            hashes.sort(key=lambda k: sortkey(k[0]))
            self.hashes = OrderedDict(hashes)
        else:
            self.hashes = dict(hashes)

    def __getitem__(self, member):
        cache = {}
        for i in range(len(self.fields)):
            cache[self.fields[i]] = loads(
                self.result[self.hashes[str(member)] + i])

        return self.SearchHash(self.tokey(member), cache)

    def __iter__(self):
        yield from self.hashes
