import pickle
import redis

r = redis.StrictRedis(host='localhost', port=6379, db=0)


def get(key):
    return pickle.loads(r.get(key))


def set(key, value=None):
    if type(key) is dict:
        for k, v in key.items():
            r.set(k, pickle.dumps(v))
    else:
        r.set(key, pickle.dumps(value))
