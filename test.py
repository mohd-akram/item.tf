import json
import tf2api
import tf2search
import cProfile

setup = """
with open('api_key.txt') as f:
    key = f.read()

schema = tf2api.getschema(key)

items = tf2api.getitems(schema)
itemsbyname = tf2api.getitemsbyname(items)

attributes = tf2api.getattributes(schema)
storeprices = tf2api.getstoreprices(key)
marketprices = tf2api.getmarketprices(itemsbyname)

with open('blueprints.json') as f:
    data = json.loads(f.read().decode('utf-8'))
    blueprints = tf2search.parseblueprints(data,itemsbyname)

itemsdict = tf2search.getitemsdict(items,attributes,blueprints,storeprices,marketprices)
"""

cProfile.run(setup)
cProfile.run("tf2search.search('engi hats',itemsdict)")
cProfile.run("tf2search.search('all',itemsdict)")