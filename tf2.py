import json
import logging
import time
from xml.dom.minidom import getDOMImplementation

import tf2api
import tf2search

from handler import Handler, memcache

def gethomepage():
    return 'http://www.tf2find.com'

def getapikey():
    with open('api_key.txt') as f:
        apikey = f.read()
    return apikey

def updatecache():
    apikey = getapikey()
    schema = tf2api.getschema(apikey)
    items = tf2api.getitems(schema)
    attributes = tf2api.getattributes(schema)

    storeprices = tf2api.getstoreprices(apikey)

    itemsbyname = tf2api.getitemsbyname(items)
    marketprices = tf2api.getmarketprices(itemsbyname)

    with open('blueprints.json') as f:
        data = json.loads(f.read().decode('utf-8'))

    blueprints = tf2search.parseblueprints(data,itemsbyname)

    itemsdict = tf2search.getitemsdict(items,attributes,blueprints,storeprices,marketprices)

    itemnames = []

    homepage = gethomepage()
    sitemap = Sitemap()
    sitemap.add(homepage)

    for name,item in itemsbyname.items():
        if not item['image_url']:
            del itemsbyname[name]
        else:
            itemnames.append(name)

            path = '{0}/item/{1}'.format(homepage,item['defindex'])
            sitemap.add(path)

    memcache.set('itemsdict', itemsdict)
    memcache.set('itemsbyname', itemsbyname)
    memcache.set('itemnames', itemnames)
    memcache.set('sitemap',sitemap.toxml())

def getfromcache(key):
    if not memcache.get(key):
        updatecache()

    return memcache.get(key)

class TF2Handler(Handler):
    def get(self):
        if self.request.host.endswith('appspot.com'):
            return self.redirect(gethomepage(), True)

        query = self.request.get('items')
        if not query:
            self.render('tf2.html')
        elif query == 'all':
            itemnames = getfromcache('itemnames')
            self.write(json.dumps(itemnames))

class TF2SearchHandler(Handler):
    def get(self):
        t0 = time.time()
        query = self.request.get('q')

        if query:
            itemsdict = getfromcache('itemsdict')
            itemsbyname = getfromcache('itemsbyname')

            if query in itemsbyname:
                return self.redirect('/item/{}'.format(itemsbyname[query]['defindex']))

            result = tf2search.search(query, itemsdict)

            t1 = time.time()

            self.render('tf2results.html',
                        query=query,
                        classitems=result['classitems'],
                        allclassitems=result['allclassitems'],
                        searchitems=result['searchitems'],
                        time=round(t1-t0,3))
        else:
            self.redirect('/')

class TF2ItemHandler(Handler):
    def get(self, defindex, is_json):
        itemsdict = getfromcache('itemsdict')
        index = int(defindex)

        if index in itemsdict:
            itemdict = itemsdict[index]
        else:
            return self.redirect('/')

        if is_json:
            self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
            self.write(json.dumps(itemdict,indent=2))
        else:
            desc_list = []

            if itemdict['description']:
                desc_list.append(itemdict['description'].replace('\n',' '))

            desc_list.append(', '.join(itemdict['classes']) if itemdict['classes'] else 'All Classes')

            if itemdict['tags']:
                desc_list.append(', '.join(itemdict['tags']).title())

            self.render('tf2item.html',item=itemdict,description=' | '.join(desc_list))

class TF2SitemapHandler(Handler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/xml; charset=UTF-8'
        self.write(getfromcache('sitemap'))

class Sitemap:
    def __init__(self):
        impl = getDOMImplementation()
        self.doc = impl.createDocument(None,'urlset',None)

        self.urlset = self.doc.documentElement
        self.urlset.setAttribute('xmlns','http://www.sitemaps.org/schemas/sitemap/0.9')

    def add(self,path):
        url = self.doc.createElement('url')
        loc = url.appendChild(self.doc.createElement('loc'))
        loctext = loc.appendChild(self.doc.createTextNode(path))

        return self.urlset.appendChild(url)

    def toxml(self):
        return self.doc.toprettyxml(encoding='UTF-8')