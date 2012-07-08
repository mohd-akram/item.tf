import json
import tf2api
import tf2search
import cProfile

setup = """
with open('api_key.txt') as f:
    key = f.read()

items = tf2api.getitems(key)
itemsbyname = tf2api.getitemsbyname(items)
storeprices = tf2api.getstoreprices(key)
marketprices = tf2api.getmarketprices(itemsbyname)

with open('blueprints.json') as f:
    blueprints = json.loads(f.read().decode('utf-8'))
    blueprints = tf2search.parseblueprints(blueprints,itemsbyname)

itemsdict = tf2search.getitemsdict(items,storeprices,marketprices,blueprints)
"""

cProfile.run(setup)
cProfile.run("tf2search.search('engi hats',itemsdict)")
cProfile.run("tf2search.search('all',itemsdict)")
