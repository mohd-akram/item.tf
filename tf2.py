import json
import logging
import time

import tf2api
import tf2search

from handler import Handler, memcache

def getfooter(time=''):
    if time:
        time = '{} seconds<br>'.format(time)
    return '{}Developed by <a href="http://steamcommunity.com/id/thefilmore">filmore</a>. Powered by <a href="http://steampowered.com">Steam</a>'.format(time)

def getapikey():
    with open('api_key.txt') as f:
        apikey = f.read()
    return apikey

def getitems():
    items = memcache.get('items')
    if not items:
        items = tf2api.getitems(getapikey())
        memcache.set('items', items)
    return items

def getitemsdict():
    itemsdict = memcache.get('itemsdict')

    if not itemsdict:
        storeprices = tf2api.getstoreprices(getapikey())
        marketprices = tf2api.getmarketprices(getitems())
        itemsdict = tf2search.getitemsdict(getitems(),storeprices,marketprices)
        memcache.set('itemsdict', itemsdict)

    return itemsdict

class TF2Handler(Handler):
    def get(self):
        self.render('tf2.html',footer=getfooter())

class TF2ResultsHandler(Handler):
    def get(self):
        t0 = time.time()

        query = self.request.get('q')
        items = getitems()
        itemsdict = getitemsdict()
        result = tf2search.search(query, items, itemsdict)

        t1 = time.time()

        timetaken = round(t1-t0,3)

        self.render('tf2results.html',
                    query=query,
                    classitems=result['classitems'],
                    allclassitems=result['allclassitems'],
                    searchitems=result['searchitems'],
                    footer=getfooter(timetaken))

class TF2ItemHandler(Handler):
    def get(self, defindex, is_json):
        itemsdict = getitemsdict()
        defindex = int(defindex)

        if defindex in itemsdict:
            itemdict = itemsdict[defindex]
        else:
            self.redirect('/')
            return

        if is_json:
            self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
            self.write(json.dumps(itemdict))
        else:
            self.render('tf2item.html',item=itemdict,footer=getfooter())