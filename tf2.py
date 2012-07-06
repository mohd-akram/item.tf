import json
import logging
import time

from tf2api import getitems, getstoreprices, getmarketprices
from tf2search import search, getitemsdict

from handler import Handler, memcache

ITEMS = memcache.get('items')
ITEMS_DICT = memcache.get('itemsdict')

FOOTER = 'Developed by <a href="http://steamcommunity.com/id/thefilmore">filmore</a>. Powered by <a href="http://steampowered.com">Steam</a>'

if not (ITEMS and ITEMS_DICT):
    t0 = time.clock()
    with open('api_key.txt') as f:
        apikey = f.read()

    ITEMS = getitems(apikey)
    storeprices= getstoreprices(apikey)
    marketprices = getmarketprices(ITEMS)
    ITEMS_DICT = getitemsdict(ITEMS,storeprices,marketprices)

    memcache.set('items', ITEMS)
    memcache.set('itemsdict',ITEMS_DICT)
    t1 = time.clock()
    logging.info('Time taken to update cache - {} seconds'.format(t1-t0))

class TF2Handler(Handler):
    def get(self):
        self.render('tf2.html',footer=FOOTER)

class TF2ResultsHandler(Handler):
    def get(self):
        query = self.request.get('q')
        items = search(query, ITEMS, ITEMS_DICT)

        self.render('tf2results.html',
                    query=query,
                    classitems=items['classitems'],
                    allclassitems=items['allclassitems'],
                    searchitems=items['searchitems'],
                    footer=FOOTER)

class TF2ItemHandler(Handler):
    def get(self, defindex, is_json):
        defindex = int(defindex)
        if defindex in ITEMS_DICT:
            itemdict = ITEMS_DICT[defindex]
        else:
            self.redirect('/')
            return

        if is_json:
            self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
            self.write(json.dumps(itemdict))
        else:
            self.render('tf2item.html',item=itemdict,footer=FOOTER)