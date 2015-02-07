#!/usr/bin/env python3
import time
from xml.dom.minidom import getDOMImplementation

import cache
import config
import tf2search

from main import getitemkey


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


def main():
    tf2info = tf2search.gettf2info(config.apikey,
                                   config.backpackkey, config.tradekey,
                                   config.blueprintsfile)

    suggestions = [[], [], []]

    sitemap = Sitemap()
    sitemap.add(config.homepage)

    for name, item in tf2info.itemsbyname.items():
        index = item['defindex']
        itemdict = tf2search.createitemdict(index, tf2info)

        if tf2search.isvalidresult(itemdict):
            cache.hset('itemnames', {name: index})

            path = '{0}/{1}'.format(config.homepage, index)

            suggestions[0].append(name)
            suggestions[1].append('{} - {}'.format(
                ', '.join(itemdict['classes']), ', '.join(itemdict['tags'])))
            suggestions[2].append(path)

            sitemap.add(path)

    for itemdict in tf2search.getitemsdict(tf2info):
        cache.set(getitemkey(itemdict['index']), itemdict)
        cache.sadd('items', itemdict['index'])

    for index in tf2info.newstoreprices:
        cache.sadd('newitems', index)

    data = {'itemsets': tf2info.itemsets,
            'bundles': tf2info.bundles,
            'suggestions': suggestions,
            'sitemap': sitemap.toxml(),
            'lastupdated': time.time()}

    cache.set(data)

if __name__ == '__main__':
    main()
