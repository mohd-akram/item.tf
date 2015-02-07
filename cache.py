import pickle
from collections.abc import Mapping

import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)


def get(key):
    return pickle.loads(r.get(key))


def set(key, value=None):
    if type(key) is dict:
        for k, v in key.items():
            r.set(k, pickle.dumps(v))
    else:
        return r.set(key, pickle.dumps(value))


def hget(key, field):
    return pickle.loads(r.hget(key, field))


def hgetall(key):
    return {k.decode(): pickle.loads(v) for k, v in r.hgetall(key).items()}


def hset(key, value):
    if len(value) == 1:
        k, v = tuple(value.items())[0]
        return r.hset(key, k, pickle.dumps(v))
    else:
        return r.hmset(key, {k: pickle.dumps(v) for k, v in value.items()})


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
        yield from hgetall(self.key)

    def __len__(self):
        return r.hlen(self.key)


class StringSet(Mapping):
    def __init__(self, key, tokey, sortkey=None):
        self.key = key
        self.tokey = tokey
        self.sortkey = sortkey

    def __getitem__(self, field):
        return get(self.tokey(field))

    def __contains__(self, field):
        return r.sismember(self.key, self.tokey(field))

    def __iter__(self):
        if self.sortkey:
            yield from sorted(smembers(self.key), key=self.sortkey)
        else:
            yield from smembers(self.key)

    def __len__(self):
        return r.scard(self.key)
