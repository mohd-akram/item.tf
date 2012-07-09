import json
import logging
import time

import tf2api
import tf2search

from handler import Handler, memcache

def getfooter(time=''):
    if time:
        time = '{} seconds<br>'.format(time)
    return (time+'Developed by <a href="http://steamcommunity.com/id/thefilmore">filmore</a> '
            '(<a href="https://github.com/mohd-akram/tf2find">GitHub</a>). '
            'Powered by <a href="http://steampowered.com">Steam</a>.')

def getapikey():
    with open('api_key.txt') as f:
        apikey = f.read()
    return apikey

def getitemsdict():
    itemsdict = memcache.get('itemsdict')

    if not itemsdict:
        apikey = getapikey()
        items = tf2api.getitems(apikey)
        itemsbyname = tf2api.getitemsbyname(items)
        storeprices = tf2api.getstoreprices(apikey)
        marketprices = tf2api.getmarketprices(itemsbyname)

        with open('blueprints.json') as f:
            data = json.loads(f.read().decode('utf-8'))

        blueprints = tf2search.parseblueprints(data,itemsbyname)

        itemsdict = tf2search.getitemsdict(items,storeprices,marketprices,blueprints)
        memcache.set('itemsdict', itemsdict)

    return itemsdict

class TF2Handler(Handler):
    def get(self):
        self.render('tf2.html',footer=getfooter())

class TF2ResultsHandler(Handler):
    def get(self):
        query = self.request.get('q')

        if query:
            t0 = time.time()

            itemsdict = getitemsdict()
            result = tf2search.search(query, itemsdict)

            t1 = time.time()

            timetaken = round(t1-t0,3)

            self.render('tf2results.html',
                        query=query,
                        classitems=result['classitems'],
                        allclassitems=result['allclassitems'],
                        searchitems=result['searchitems'],
                        footer=getfooter(timetaken))
        else:
            self.redirect('/')

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