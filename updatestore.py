#!/usr/bin/env python3
import sys
import time
import asyncio
from xml.dom.minidom import getDOMImplementation

from aioredis import create_redis
from slugify import slugify

import config
import tf2search
from store import Redis
from main import getitemkey, getclasskey, gettagkey


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
        return self.doc.toprettyxml()


async def main(flush):
    store = await create_redis(('localhost', 6379), commands_factory=Redis)

    tf2info = tf2search.gettf2info(config.apikey,
                                   config.backpackkey, config.tradekey,
                                   config.blueprintsfile)

    if flush:
        await store.delete('items')
        await store.delete_all('items:*')
        await store.delete_all('item:*')

    suggestions = [[], [], []]

    sitemap = Sitemap()
    sitemap.add(config.homepage)

    categories = {
        'cosmetics': ('hats', 'miscs'),
        'weapons': ('primary', 'secondary', 'melee')
    }

    for category, subcategories in categories.items():
        sitemap.add(f'{config.homepage}/{category}')
        for subcategory in subcategories:
            sitemap.add(f'{config.homepage}/{category}/{subcategory}')

    for index in tf2info.items:
        pipe = store.pipeline()

        itemdict = tf2search.createitemdict(index, tf2info)
        name = itemdict['name']

        pipe.hmset_dict(getitemkey(index), itemdict)
        pipe.sadd('items', index)

        classes = itemdict['classes']
        tags = itemdict['tags']

        if index == tf2info.itemsbyname[name]['defindex']:
            if tf2search.isvalidresult(itemdict, False):
                if not classes:
                    pipe.sadd(getclasskey(), index)
                if len(classes) > 1:
                    pipe.sadd(getclasskey(multi=True), index)
                if not tags:
                    pipe.sadd(gettagkey(), index)
                for class_ in classes:
                    pipe.sadd(getclasskey(class_), index)
                for tag in tags:
                    pipe.sadd(gettagkey(tag), index)

            if tf2search.isvalidresult(itemdict):
                slug = slugify(name)

                pipe.sadd('items:indexes', index)
                pipe.hmset_dict('items:slugs', {slug: index})
                pipe.hmset_dict('items:names', {name: index})

                path = f'{config.homepage}/{slug}'

                suggestions[0].append(name)
                suggestions[1].append('{} - {}'.format(
                    ', '.join(itemdict['classes']),
                    ', '.join(itemdict['tags'])))
                suggestions[2].append(path)

                sitemap.add(path)

        await pipe.execute()

    await store.delete('items:new')
    for index in tf2info.newstoreprices:
        await store.sadd('items:new', index)

    bundles = {str(k): v for k, v in tf2info.bundles.items()}

    data = {'items:sets': tf2info.itemsets,
            'items:bundles': bundles,
            'items:suggestions': suggestions,
            'items:lastupdated': time.time(),
            'sitemap': sitemap.toxml()}

    await store.mset_dict(data)


if __name__ == '__main__':
    flush = len(sys.argv) == 2 and sys.argv[1] == '-f'
    asyncio.get_event_loop().run_until_complete(main(flush))
