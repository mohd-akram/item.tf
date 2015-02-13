#!/usr/bin/env python3
import os
import time
import random
import logging

from bottle import (get, error, request, response, redirect, static_file,
                    run, default_app)
import jinja2
import ujson

import cache
import config
import tf2api
import tf2search

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True, trim_blocks=True)


@get('/')
def home():
    t0 = cache.get('lastupdated')
    lastupdated = int(time.time() - t0) // 60

    newitems = tuple(
        getitem(k) for k in cache.srandmember('newitems', 5))

    return render('home.html',
                  homepage=config.homepage,
                  tags=tf2api.getalltags(),
                  newitems=newitems,
                  message=random.choice(config.messages),
                  lastupdated=lastupdated)


@get('/<index:int><is_json:re:(\.json)?>')
def item(index, is_json):
    item = getitem(index)

    if not item:
        if is_json:
            return {'error': 'Item does not exist.'}
        return redirect('/')

    if is_json:
        return item
    else:
        desc_list = []

        if item['description']:
            desc_list.append(item['description'].replace('\n', ' '))

        desc_list.append(', '.join(item['classes'])
                         if item['classes'] else 'All Classes')

        if item['tags']:
            desc_list.append(', '.join(item['tags']).title())

        return render('item.html',
                      item=item,
                      description=' | '.join(desc_list))


@get('/search<is_json:re:(\.json)?>')
def search(is_json):
    query = request.query.q

    if not query:
        if is_json:
            return {'error': 'No query provided.'}
        return redirect('/')

    elif query == 'random':
        index = cache.srandmember('items:indexes')
        return redirect('/{}{}'.format(index, is_json))

    itemnames = cache.Hash('items:names')

    if query in itemnames:
        return redirect('/{}'.format(itemnames[query]))

    t0 = time.time()

    if query == 'all':
        items = cache.Hashes(
            [getitemkey(k) for k in cache.sort('items')])
        results = [tf2search.getsearchresult(items=items)]
    else:
        sources = ('backpack.tf', 'trade.tf')
        pricesource = request.get_cookie('price_source')
        if pricesource not in sources:
            pricesource = sources[0]

        items = cache.HashSet('items', getitemkey)
        results = tf2search.visualizeprice(query, items, pricesource)

        input_ = tf2search._parseinput(query)
        classes = input_['classes']
        tags = input_['tags']

        if results is not None:
            if len(results) != 0:
                for item in results[0]['items']:
                    item['item'] = item['item'].todict()

                if not is_json:
                    items = []
                    for item in results[0]['items']:
                        items.extend([item['item']] * item['count'])
                    results[0]['items'] = items

        elif classes or tags:
            results = getresults(classes, tags)

        else:
            itemsdict = cache.SearchHashSet(
                'items', getitemkey,
                ('index', 'name', 'image', 'classes', 'tags', 'marketprice'),
                int)

            itemsets = cache.get('itemsets')
            bundles = cache.get('bundles')

            results = tf2search.search(query, itemsdict, itemnames,
                                       itemsets, bundles, pricesource)

            for result in results:
                result['items'] = cache.Hashes(
                    [h.key for h in result['items']])

    t1 = time.time()

    if is_json:
        return tojson(results)
    else:
        return render('search.html',
                      query=query,
                      results=results,
                      count=sum(len(result['items']) for result in results),
                      time=round(t1 - t0, 3))


@get('/suggest')
def suggest():
    query = request.query.q

    allsuggestions = cache.get('suggestions')
    suggestions = [query, [], [], []]

    if query:
        for name, desc, path in zip(*allsuggestions):
            foldedname = tf2search.foldaccents(name)

            if query in foldedname or query in foldedname.lower():
                suggestions[1].append(name)
                suggestions[2].append(desc)
                suggestions[3].append(path)
    else:
        suggestions[1:] = allsuggestions

    return tojson(suggestions)


@get('/sitemap.xml')
def sitemap():
    response.set_header('Content-Type', 'application/xml;charset=UTF-8')
    return cache.get('sitemap')


@get('/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static')


@error(500)
def error500(error):
    logging.exception(error)
    return render('error.html')


def render(template, **params):
    """Render HTML template"""
    t = jinja_env.get_template(template)
    return t.render(params)


def tojson(*args, **kwargs):
    response.set_header('Content-Type', 'application/json;charset=UTF-8')
    return ujson.dumps(*args,  **kwargs)


def getresults(classes, tags):
    key = getsearchkey(classes, tags)
    multikey = getsearchkey(classes, tags, 'Multi')
    allkey = getsearchkey(classes, tags, 'All')

    keys = (key, multikey, allkey)
    titles = ('', 'Multi-Class Items', 'All-Class Items')

    if not cache.exists(key) and not cache.exists(allkey):
        classkeys = [getclasskey(class_) for class_ in classes] or 'items'
        tagkeys = [gettagkey(tag) for tag in tags] or 'items'

        classeskey = 'temp:classes'
        tagskey = 'temp:tags'

        pipe = cache.pipeline()

        pipe.sunionstore(classeskey, classkeys)
        pipe.sunionstore(tagskey, tagkeys)

        remove = []
        # Remove tokens when searching for weapons
        if 'weapon' in tags and not tags.isdisjoint(tf2api.getweapontags()):
            remove.append(gettagkey('token'))
        # Hide medals if not explicitly searching for them
        if 'tournament' not in tags:
            remove.append(gettagkey('tournament'))
        if remove:
            pipe.sdiffstore(tagskey, [tagskey] + remove)

        pipe.sinterstore(key, [classeskey, tagskey])
        pipe.sinterstore(multikey, [key, getclasskey(multi=True)])
        pipe.sinterstore(allkey, [tagskey, getclasskey()])
        pipe.sdiffstore(key, [key, multikey, allkey])

        pipe.delete(classeskey)
        pipe.delete(tagskey)

        for k in keys:
            pipe.sort(k, store=k)
            pipe.expire(k, 3600)

        pipe.execute()

    getkeys = lambda key: [getitemkey(k) for k in cache.lrange(key, 0, -1)]

    results = []
    for title, key in zip(titles, keys):
        itemkeys = getkeys(key)
        if itemkeys:
            results.append(tf2search.getsearchresult(
                title=title, items=cache.Hashes(itemkeys)))

    return results


def getsearchkey(classes=None, tags=None, type_=''):
    concat = lambda l: ','.join(sorted(l)) if l else '*'
    return 'items:search:classes={}:tags={}:{}'.format(concat(classes),
                                                       concat(tags), type_)


def getclasskey(class_=None, multi=False):
    class_ = 'Multi' if multi else (class_ or 'All')
    return 'items:class:{}'.format(class_)


def gettagkey(tag=None):
    return 'items:tag:{}'.format(tag or 'none')


def getitem(index):
    return cache.hgetall(getitemkey(index))


def getitemkey(index):
    return 'item:{}'.format(index)


if __name__ == '__main__':
    run(host='localhost', port=8080, reloader=True)

app = default_app()
