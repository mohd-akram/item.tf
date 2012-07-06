import tf2api
import tf2search
import cProfile

setup = """
with open('api_key.txt') as f:
    key = f.read()

items = tf2api.getitems(key)
storeprices = tf2api.getstoreprices(key)
marketprices = tf2api.getmarketprices(items)

itemsdict = tf2search.getitemsdict(items,storeprices,marketprices)
"""

cProfile.run(setup)
cProfile.run("tf2search.search('engi hats',itemsdict)")
cProfile.run("tf2search.search('all',itemsdict)")