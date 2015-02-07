#!/usr/bin/env python3
import time
from xml.dom.minidom import getDOMImplementation

import cache
import config
import tf2search


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

    itemsdict = tf2search.getitemsdict(tf2info)

    newitems = [itemsdict[index] for index in tf2info.newstoreprices]

    nametoindexmap = {}
    itemindexes = set()
    suggestions = [[], [], []]

    sitemap = Sitemap()
    sitemap.add(config.homepage)

    for name, item in tf2info.itemsbyname.items():
        index = item['defindex']
        itemdict = itemsdict[index]

        if tf2search.isvalidresult(itemdict):
            nametoindexmap[name] = index
            itemindexes.add(index)

            path = '{0}/{1}'.format(config.homepage, index)

            suggestions[0].append(name)
            suggestions[1].append('{} - {}'.format(
                ', '.join(itemdict['classes']), ', '.join(itemdict['tags'])))
            suggestions[2].append(path)

            sitemap.add(path)

    data = {'itemsdict': itemsdict,
            'itemsets': tf2info.itemsets,
            'bundles': tf2info.bundles,
            'nametoindexmap': nametoindexmap,
            'itemindexes': itemindexes,
            'newitems': newitems,
            'suggestions': suggestions,
            'sitemap': sitemap.toxml(),
            'lastupdated': time.time()}

    cache.set(data)

if __name__ == '__main__':
    main()
