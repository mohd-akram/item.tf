"""This module contains all the page handlers and caching mechanisms."""
import json
import logging
import time
import random
from xml.dom.minidom import getDOMImplementation
from google.appengine.api import memcache

import tf2api
import tf2search

from handler import Handler


def gethomepage():
    return 'http://www.tf2find.com'


def getapikey():
    with open('api_key.txt') as f:
        apikey = f.read()
    return apikey


def updatecache():
    t0 = time.time()
    apikey = getapikey()

    schema = tf2api.getschema(apikey)
    itemsets = tf2api.getitemsets(schema)
    storeprices = tf2api.getstoreprices(apikey)
    bundles = tf2api.getbundles(apikey, storeprices)

    itemsbyname = tf2api.getitemsbyname(schema)
    marketprices = tf2api.getmarketprices(itemsbyname)

    with open('blueprints.json') as f:
        data = json.loads(f.read().decode('utf-8'))
    blueprints = tf2search.parseblueprints(data, itemsbyname)

    itemsdict = tf2search.getitemsdict(schema, bundles, blueprints,
                                       storeprices, marketprices)
    newitems = [itemsdict[index] for index in
                tf2api.getnewstoreprices(storeprices)]

    nametoindexmap = {}
    itemnames = []
    itemindexes = []

    homepage = gethomepage()
    sitemap = Sitemap()
    sitemap.add(homepage)

    for name, item in itemsbyname.items():
        index = item['defindex']
        itemdict = itemsdict[index]

        if tf2search.isvalidresult(itemdict):
            nametoindexmap[name] = index
            itemnames.append(name)
            itemindexes.append(index)

            path = '{0}/item/{1}'.format(homepage, index)
            sitemap.add(path)

    memcache.set_multi({'itemsdict': itemsdict,
                        'itemsets': itemsets,
                        'bundles': bundles,
                        'nametoindexmap': nametoindexmap,
                        'itemnames': itemnames,
                        'itemindexes': itemindexes,
                        'newitems': newitems,
                        'sitemap': sitemap.toxml()})
    t1 = time.time()

    memcache.set('lastupdated', t1)
    logging.debug('Updated Cache. Time taken: {} seconds'.format(t1 - t0))


def getfromcache(key):
    value = memcache.get(key)

    if not value:
        logging.debug('Cache is empty')
        updatecache()
        value = memcache.get(key)

    return value


class TF2Handler(Handler):
    """Homepage handler"""
    def get(self):
        if self.request.host.endswith('appspot.com'):
            return self.redirect(gethomepage(), True)

        t0 = getfromcache('lastupdated')
        lastupdated = int(time.time() - t0) / 60

        self.render('tf2.html',
                    homepage=gethomepage(),
                    tags=tf2api.getalltags(),
                    newitems=random.sample(getfromcache('newitems'), 5),
                    lastupdated=lastupdated)


class TF2SearchHandler(Handler):
    def get(self):
        query = self.request.get('q')

        if query:
            nametoindexmap = getfromcache('nametoindexmap')

            if query in nametoindexmap:
                return self.redirect(
                    '/item/{}'.format(nametoindexmap[query]))

            elif query == 'random':
                itemindexes = getfromcache('itemindexes')
                return self.redirect(
                    '/item/{}'.format(random.choice(itemindexes)))

            itemsdict = getfromcache('itemsdict')
            itemsets = getfromcache('itemsets')
            bundles = getfromcache('bundles')

            t0 = time.time()
            results = tf2search.search(query, itemsdict, nametoindexmap,
                                       itemsets, bundles)
            t1 = time.time()

            self.render('tf2results.html',
                        query=query,
                        mainitems=results['mainitems'],
                        otheritems=sorted(results['otheritems'].items(),
                                          key=lambda k: len(k[0]),
                                          reverse=True),
                        itemsets=itemsets,
                        resultslength=results['length'],
                        time=round(t1 - t0, 3))
        else:
            self.redirect('/')


class TF2SuggestHandler(Handler):
    """OpenSearch suggestions handler"""
    def get(self):
        query = self.request.get('q')

        itemnames = getfromcache('itemnames')
        if query:
            suggestions = []
            for name in itemnames:
                if query in name or query in name.lower():
                    suggestions.append(name)
        else:
            suggestions = itemnames

        self.response.headers['Content-Type'] = ('application/json;'
                                                 'charset=UTF-8')
        self.write(json.dumps([query, suggestions]))


class TF2ItemHandler(Handler):
    def get(self, defindex, is_json):
        itemsdict = getfromcache('itemsdict')
        index = int(defindex)

        if index in itemsdict:
            itemdict = itemsdict[index]
        else:
            return self.redirect('/')

        if is_json:
            self.response.headers['Content-Type'] = ('application/json;'
                                                     'charset=UTF-8')
            self.write(json.dumps(itemdict, indent=2))
        else:
            desc_list = []

            if itemdict['description']:
                desc_list.append(itemdict['description'].replace('\n', ' '))

            desc_list.append(', '.join(itemdict['classes'])
                             if itemdict['classes'] else 'All Classes')

            if itemdict['tags']:
                desc_list.append(', '.join(itemdict['tags']).title())

            self.render('tf2item.html',
                        item=itemdict,
                        description=' | '.join(desc_list))


class TF2SitemapHandler(Handler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/xml;charset=UTF-8'
        self.write(getfromcache('sitemap'))


class CacheHandler(Handler):
    def get(self, option):
        if option == 'update':
            updatecache()
            self.write('Cache Updated')
        elif option == 'flush':
            memcache.flush_all()
            self.write('Cache Flushed')


class Sitemap:
    """A class that is used to create XML sitemaps"""
    def __init__(self):
        impl = getDOMImplementation()
        self.doc = impl.createDocument(None, 'urlset', None)

        self.urlset = self.doc.documentElement
        self.urlset.setAttribute('xmlns',
                                 'http://www.sitemaps.org/schemas/sitemap/0.9')

    def add(self, path):
        """Add a url to the sitemap"""
        url = self.doc.createElement('url')
        loc = url.appendChild(self.doc.createElement('loc'))
        loc.appendChild(self.doc.createTextNode(path))

        return self.urlset.appendChild(url)

    def toxml(self):
        """Return a pretty XML version of the sitemap"""
        return self.doc.toprettyxml(encoding='UTF-8')
