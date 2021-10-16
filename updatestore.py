#!/usr/bin/env python3
import sys
import time
import asyncio
from xml.dom.minidom import getDOMImplementation

from slugify import slugify

import config
import tf2api
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
    store = Redis.from_url('redis://localhost')

    tf2info = await tf2search.gettf2info(config.apikey,
                                         config.backpackkey,
                                         config.blueprintsfile)

    if flush:
        await store.delete('items')
        await store.delete_all('items:*')
        await store.delete_all('item:*')

    suggestions = [[], [], []]

    sitemap = Sitemap()
    sitemap.add(config.homepage)

    all_classes = [class_.lower() for class_ in tf2api.getallclasses()]
    all_tags = list(tf2api.getalltags())
    all_qualities = [quality.replace("'", '').lower() for quality in
                     tf2api.getallqualities().values()]

    keywords = all_classes + all_tags + all_qualities
    for keyword in keywords:
        sitemap.add(f'{config.homepage}/search/{keyword}')

    for class_tag in all_classes + all_tags:
        for quality in all_qualities:
            sitemap.add(f'{config.homepage}/search/{quality}-{class_tag}')

    for class_ in all_classes:
        for tag in all_tags:
            sitemap.add(f'{config.homepage}/search/{class_}-{tag}')
            for quality in all_qualities:
                sitemap.add(
                    f'{config.homepage}/search/{quality}-{class_}-{tag}'
                )

    for index in tf2info.items:
        async with store.pipeline() as pipe:
            itemdict = tf2search.createitemdict(index, tf2info)
            name = itemdict['name']

            pipe.hset(getitemkey(index), mapping=itemdict)
            pipe.sadd('items', index)

            classes = itemdict['classes']
            tags = itemdict['tags']

            if index == tf2info.itemsbyname[name]['defindex']:
                slug = slugify(name)

                pipe.hset('items:slugs', mapping={slug: index})

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
                    pipe.sadd('items:indexes', index)
                    pipe.hset('items:names', mapping={name: index})

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

    await store.mset(data)


if __name__ == '__main__':
    flush = len(sys.argv) == 2 and sys.argv[1] == '-f'
    asyncio.run(main(flush))
