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
        schema = tf2api.getschema(apikey)
        items = tf2api.getitems(schema)
        attributes = tf2api.getattributes(schema)

        itemsbyname = tf2api.getitemsbyname(items)
        memcache.set('itemsbyname', itemsbyname)

        storeprices = tf2api.getstoreprices(apikey)
        marketprices = tf2api.getmarketprices(itemsbyname)

        with open('blueprints.json') as f:
            data = json.loads(f.read().decode('utf-8'))

        blueprints = tf2search.parseblueprints(data,itemsbyname)

        itemsdict = tf2search.getitemsdict(items,attributes,blueprints,storeprices,marketprices)
        memcache.set('itemsdict', itemsdict)

        exclusions = tf2search.getexclusions()
        itemnames = [i['name'] for i in itemsdict.values() if i['index'] not in exclusions]
        memcache.set('itemnames', itemnames)

    return itemsdict

class TF2Handler(Handler):
    def get(self):
        query = self.request.get('items')
        itemnames = memcache.get('itemnames')
        if not query:
            self.render('tf2.html',footer=getfooter())
        elif query == 'all' and itemnames:
            self.write(json.dumps(itemnames))

class TF2ResultsHandler(Handler):
    def get(self):
        t0 = time.time()
        query = self.request.get('q')

        if query:
            itemsbyname = memcache.get('itemsbyname')
            if itemsbyname:
                if query in itemsbyname:
                    self.redirect('/item/{}'.format(itemsbyname[query]['defindex']))
                    return

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
            self.write(json.dumps(itemdict,indent=2))
        else:
            self.render('tf2item.html',item=itemdict,footer=getfooter())