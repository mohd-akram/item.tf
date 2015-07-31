#!/usr/bin/env python3
import os
import time
import random
import logging
from base64 import b64encode
from datetime import datetime, timedelta
from urllib.parse import urlparse
from urllib.error import HTTPError

import jinja2
import ujson
from bottle import (get, post, error, request, response, redirect, static_file,
                    run, default_app)
from openid.consumer import consumer

import config
import tf2api
import tf2search
from store import Redis

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True, trim_blocks=True)

store = Redis(host='localhost', port=6379, db=0)

session_age = timedelta(weeks=2)
login_verify_url = '{}/login/verify'.format(config.homepage)


@get('/')
def home():
    t0 = store.get('items:lastupdated')
    lastupdated = int(time.time() - t0) // 60

    newitems = getitems(store.srandmember('items:new', 5))

    return render('home.html',
                  homepage=config.homepage,
                  user=getcurrentuser(),
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
        index = store.srandmember('items:indexes')
        return redirect('/{}{}'.format(index, is_json))

    itemnames = store.Hash('items:names')

    if query in itemnames:
        return redirect('/{}'.format(itemnames[query]))

    t0 = time.time()

    if query == 'all':
        items = store.Hashes(
            [getitemkey(k) for k in store.sort('items')])
        results = [tf2search.getsearchresult(items=items)]
    else:
        sources = ('backpack.tf', 'trade.tf')
        pricesource = request.get_cookie('price_source')
        if pricesource not in sources:
            pricesource = sources[0]

        items = store.HashSet('items', getitemkey)
        results = tf2search.visualizeprice(query, items, pricesource)

        input_ = tf2search.parseinput(query)
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
            itemsdict = store.SearchHashSet(
                'items', getitemkey,
                ('index', 'name', 'image', 'classes', 'tags', 'marketprice'),
                int)

            itemsets = store.get('items:sets')
            bundles = store.get('items:bundles')

            results = tf2search.search(query, itemsdict, itemnames,
                                       itemsets, bundles, pricesource)

            for result in results:
                result['items'] = store.Hashes(
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


@post('/wishlist/<option:re:add|remove>')
def wishlist(option):
    user = getcurrentuser()
    userkey = getuserkey(user['id'])

    if option == 'add':
        index = int(request.forms.get('index'))
        quality = int(request.forms.get('quality'))

        if (store.sismember('items:indexes', index) and
                quality in tf2api.getallqualities()):

            if len(user['wishlist']) < 100:
                user['wishlist'].append({'index': index,
                                         'quality': quality})
                store.hset(userkey, 'wishlist', user['wishlist'])

                return 'Added'

    elif option == 'remove':
        i = int(request.forms.get('i'))

        del user['wishlist'][i]
        store.hset(userkey, 'wishlist', user['wishlist'])

        return 'Removed'


@get('/suggest')
def suggest():
    query = request.query.q

    allsuggestions = store.get('items:suggestions')
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


@get('/<urltype:re:id>/<steamid:re:[A-Za-z0-9_-]+>')
@get('/<urltype:re:profiles>/<steamid:re:[0-9]+>')
def user(urltype, steamid):
    currentuser = getcurrentuser()
    if currentuser and currentuser['url'] == request.urlparts.path:
        user = currentuser
    else:
        user = getuser(steamid, urltype)

    if user:
        if user['url'] != request.urlparts.path:
            return redirect(user['url'])

        items = getitems(item['index'] for item in user['wishlist'])

        for i, item in enumerate(items):
            item.update({'i': i})
            item.update(user['wishlist'][i])

    else:
        return redirect('/')

    return render('user.html',
                  user=user,
                  items=items)


@get('/login')
def login():
    sid = b64encode(os.urandom(16)).decode()
    session = {'sid': sid}
    expires = datetime.now() + session_age
    response.set_cookie('sid', sid, expires=expires)

    c = consumer.Consumer(session, None)
    a = c.begin('http://steamcommunity.com/openid')
    url = a.redirectURL(config.homepage, login_verify_url)

    return redirect(url)


@get('/login/verify')
def login_verify():
    sid = request.get_cookie('sid')
    session = {'sid': sid}

    c = consumer.Consumer(session, None)
    info = c.complete(request.query, login_verify_url)

    if info.status == consumer.SUCCESS:
        steamid = request.query['openid.claimed_id'].split('/')[-1]
        user = getuser(steamid, create=True)
        store.setex(getsessionkey(sid), int(session_age.total_seconds()),
                    user['id'])

    return redirect('/')


@get('/sitemap.xml')
def sitemap():
    response.set_header('Content-Type', 'application/xml;charset=UTF-8')
    return store.get('sitemap')


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
    return ujson.dumps(*args, **kwargs)


def getresults(classes, tags):
    key = getsearchkey(classes, tags)
    multikey = getsearchkey(classes, tags, 'Multi')
    allkey = getsearchkey(classes, tags, 'All')

    keys = (key, multikey, allkey)
    titles = ('', 'Multi-Class Items', 'All-Class Items')

    if not store.exists(key) and not store.exists(allkey):
        classeskey = 'temp:classes'
        tagskey = 'temp:tags'
        remove = []

        pipe = store.pipeline()

        classkeys = [getclasskey(class_) for class_ in classes] or 'items'
        pipe.sunionstore(classeskey, classkeys)

        # Get only the specified weapon types
        if 'weapon' in tags and not tags.isdisjoint(tf2api.getweapontags()):
            tags.remove('weapon')
            remove.append(gettagkey('token'))

        tagkeys = [gettagkey(tag) for tag in tags] or 'items'
        pipe.sunionstore(tagskey, tagkeys)

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

    getkeys = lambda key: [getitemkey(k) for k in store.lrange(key, 0, -1)]

    results = []
    for title, key in zip(titles, keys):
        itemkeys = getkeys(key)
        if itemkeys:
            results.append(tf2search.getsearchresult(
                title=title, items=store.Hashes(itemkeys)))

    return results


def getsearchkey(classes=None, tags=None, type_=''):
    concat = lambda l: ','.join(sorted(l)) if l else '*'
    return 'items:search:classes={}&tags={}:{}'.format(concat(classes),
                                                       concat(tags), type_)


def getclasskey(class_=None, multi=False):
    class_ = 'Multi' if multi else (class_ or 'All')
    return 'items:class:{}'.format(class_)


def gettagkey(tag=None):
    return 'items:tag:{}'.format(tag or 'none')


def getcurrentuser():
    user = None

    sid = request.get_cookie('sid')

    if sid:
        userid = store.get(getsessionkey(sid))
        if userid:
            user = getuser(userid)
            expires = datetime.now() + session_age
            response.set_cookie('steam_id', user['id'], expires=expires)
        else:
            response.delete_cookie('sid')
            response.delete_cookie('steam_id')

    return user


def getuser(steamid, urltype='profiles', create=False):
    if urltype == 'id':
        steamid = tf2api.resolvevanityurl(config.apikey, steamid)

    userkey = getuserkey(steamid)
    user = store.hgetall(userkey)

    if user:
        create = False
        lastupdate = datetime.fromtimestamp(user['lastupdate'])
        needsupdate = (datetime.now() - lastupdate) > timedelta(minutes=3)
    else:
        if not create:
            return
        user = {'id': steamid}

    if create or needsupdate:
        try:
            steamuser = tf2api.getplayersummary(config.apikey, steamid)

        except HTTPError:
            # Postpone update if this is not a new user
            if create:
                raise
            return user

        user['name'] = steamuser['personaname']
        # Remove trailing slash and parse url
        user['url'] = urlparse(steamuser['profileurl'][:-1]).path
        user['avatar'] = steamuser['avatar']
        user['state'] = ('Online' if steamuser['personastate'] != 0 else
                         'Offline')

        if 'gameid' in steamuser:
            user['state'] = 'In-Game'

        if 'wishlist' not in user:
            user['wishlist'] = []

        user['lastupdate'] = datetime.now().timestamp()

        store.hmset(userkey, user)
        store.sadd('users', user['id'])

    return user


def getuserkey(uid):
    return 'user:{}'.format(uid)


def getsessionkey(sid):
    return 'session:{}'.format(sid)


def getitems(indexes):
    return store.hgetall([getitemkey(index) for index in indexes])


def getitem(index):
    return store.hgetall(getitemkey(index))


def getitemkey(index):
    return 'item:{}'.format(index)


if __name__ == '__main__':
    run(host='localhost', port=8080)

app = default_app()
