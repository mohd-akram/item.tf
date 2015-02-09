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
        return redirect('/{}'.format(index))

    itemnames = cache.Hash('items:names')

    if query in itemnames:
        return redirect('/{}'.format(itemnames[query]))

    itemsdict = cache.SearchHashSet(
        'items', getitemkey,
        ('index', 'name', 'image', 'classes', 'tags', 'marketprice'), int)

    itemsets = cache.get('itemsets')
    bundles = cache.get('bundles')

    pricesource = request.get_cookie('price_source')

    sources = ('backpack.tf', 'trade.tf')
    if pricesource not in sources:
        pricesource = sources[0]

    t0 = time.time()
    results = tf2search.search(query, itemsdict, itemnames,
                               itemsets, bundles, pricesource)
    t1 = time.time()

    for result in results:
        result['items'] = cache.Hashes(result['items'])

    count = sum(len(result['items']) for result in results)
    if is_json:
        return tojson(results)
    else:
        return render('search.html',
                      query=query,
                      results=results,
                      count=count,
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


def getitemkey(index):
    return 'item:{}'.format(index)


def getitem(index):
    return cache.Hash(getitemkey(index)).todict()


if __name__ == '__main__':
    run(host='localhost', port=8080, reloader=True)

app = default_app()
