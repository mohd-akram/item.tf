#!/usr/bin/env python3

import os
import time
import random
import asyncio
import logging
from base64 import b64encode
from datetime import datetime, timedelta
from urllib.parse import urlparse
from urllib.error import URLError

import jinja2
import rapidjson
import uvloop
from bottle import (get, post, abort, error, request, response, redirect,
                    static_file, run, default_app)
from aioredis import create_redis
from openid.consumer import consumer
from slugify import slugify

import config
import tf2api
import tf2search
from store import Redis

logger = logging.getLogger('gunicorn.error')

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True, trim_blocks=True,
                               enable_async=True)

jinja_env.filters['slugify'] = slugify

session_age = timedelta(weeks=2)
login_verify_url = '{}/login/verify'.format(config.homepage)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def sync(f):
    def wait(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(f(*args, **kwargs))
    return wait


@sync
async def init():
    global store
    store = await create_redis(('localhost', 6379), commands_factory=Redis)


@get('/')
@sync
async def home():
    t0 = await store.get('items:lastupdated')
    lastupdated = int(time.time() - t0) // 60

    newitems = await getitems(await store.srandmember('items:new', 5))

    user = await getcurrentuser(request)

    if user:
        expires = datetime.now() + session_age
        response.set_cookie('steam_id', user['id'], expires=expires)
    else:
        response.delete_cookie('sid')
        response.delete_cookie('steam_id')

    return await render('home.html',
                        homepage=config.homepage,
                        user=user,
                        tags=tf2api.getalltags(),
                        newitems=newitems,
                        message=random.choice(config.messages),
                        lastupdated=lastupdated)


@get('/search/<slug:re:[a-z]+(?:-[0-9a-z]+)*>')
@get('/search<is_json:re:(\.json)?>')
@sync
async def search(**kwargs):
    slug = kwargs.get('slug')
    is_json = kwargs.get('is_json', '')

    query = slug.replace('-', ' ') if slug else request.query.q

    if not query:
        if is_json:
            return {'error': 'No query provided.'}
        return redirect('/')

    elif query == 'random':
        index = await store.srandmember('items:indexes')
        return redirect('/{}{}'.format(index, is_json))

    itemnames = await store.hgetall('items:names')

    if query in itemnames:
        return redirect('/{}'.format(itemnames[query]))

    t0 = time.time()

    classes = set()
    tags = set()

    priceviz = False

    if query == 'all':
        items = store.Hashes(
            [getitemkey(k.decode()) for k in await store.sort('items')])
        results = [tf2search.getsearchresult(items=items)]
    else:
        sources = ('backpack.tf', 'trade.tf')
        pricesource = request.get_cookie('price_source')
        if pricesource not in sources:
            pricesource = sources[0]

        items = {
            item['index']: item async for item in store.Hashes([
                getitemkey(143),  # Earbuds
                getitemkey(5021),  # Key
                getitemkey(5002),  # Refined
                getitemkey(5001),  # Reclaimed
                getitemkey(5000),  # Scrap
                getitemkey(0)  # Weapon
            ])
        }
        results = tf2search.visualizeprice(query, items, pricesource)

        input_ = tf2search.parseinput(query)
        classes = input_['classes']
        tags = input_['tags']

        if results is not None:
            if len(results) != 0:
                priceviz = True
                if not is_json:
                    items = []
                    for item in results[0]['items']:
                        items.extend([item['item']] * item['count'])
                    results[0]['items'] = items

        elif classes or tags:
            results = await getresults(classes, tags)

        else:
            itemsdict = await store.SearchHashSet(
                'items', getitemkey,
                ('index', 'name', 'image', 'classes', 'tags', 'marketprice'),
                int)

            itemsets = await store.get('items:sets')
            bundles = await store.get('items:bundles')

            results = tf2search.search(query, itemsdict, itemnames,
                                       itemsets, bundles, pricesource)

            for result in results:
                result['items'] = store.Hashes(
                    [h.key for h in result['items']])

    t1 = time.time()

    count = sum(len(result['items']) for result in results)

    all_classes = list(tf2api.getallclasses().keys())
    classes_text = getlistastext(sorted(classes, key=all_classes.index))
    tags_text = getlistastext(sorted(tags))

    if query == 'all':
        description = f'A list of all {count:,} items in TF2.'
    elif classes and tags:
        description = (
            f'A list of the {count:,} {tags_text} items for {classes_text}'
            ' in TF2.'
        )
    elif classes:
        description = (
            f'A list of the {count:,} items for {classes_text} in TF2.'
        )
    elif tags:
        description = f'A list of the {count:,} {tags_text} items in TF2.'
    elif priceviz:
        from_, equals, to = results[0]['title'].partition(' = ')
        to = getlistastext(to.split(' + '))
        description = (f'{from_} is the same as {to} in TF2.' if equals else
                       f'A list of {from_} items in TF2.')
    elif results and ':' in results[0]['title']:
        title = results[0]['title'].replace(':', '')
        description = f'{count:,} {title} items in TF2.'
    else:
        description = f'Search results for "{query}" items in TF2.'

    if is_json:
        for result in results:
            result['items'] = [item async for item in result['items']]
        return tojson(results)
    else:
        return await render('search.html',
                            query=query,
                            description=description,
                            results=results,
                            count=count,
                            time=round(t1 - t0, 3))


# Must be after search route and in this order
@get('/<slug:re:[a-z0-9]+(?:-[a-z0-9]+)*>')
@get('/<index:re:[0-9]+><is_json:re:(\.json)?>')
@sync
async def item(**kwargs):
    slug = kwargs.get('slug')
    index = kwargs.get('index')
    is_json = kwargs.get('is_json')

    item = await (getitembyslug(slug) if slug else getitem(index))

    if item and index is not None and not is_json:
        slug = slugify(item['name'])
        return redirect(f'/{slug}', code=301)

    if not item:
        if is_json:
            return {'error': 'Item does not exist.'}
        abort(404)

    if is_json:
        return item
    else:
        name = item['name']
        tags_text = '/'.join(item['tags']) if item['tags'] else 'item'
        classes_text = getlistastext(item['classes'], 'all classes')

        description = f'{name} is a TF2 {tags_text} for {classes_text}.'

        if item['description']:
            desc_parts = item['description'].partition('---')

            desc = desc_parts[0].replace('\n', ' ')
            bundle_items = getlistastext(desc_parts[2].split('\n'))

            description = (
                f"{description} {desc} {bundle_items}" if bundle_items else
                f"{description} {desc}"
            ).rstrip(':')

            if description[-1] not in ('.', '?', '!'):
                description += '.'

        return await render('item.html',
                            item=item,
                            description=description)


def getlistastext(l, default=''):
    return (', and '.join(l).replace(', and ', ', ', max(0, len(l) - 2))
            if l else default)


@post('/wishlist/<option:re:add|remove>')
@sync
async def wishlist(option):
    user = await getcurrentuser(request)

    if not user:
        response.status = 401
        response.headers['WWW-Authenticate'] = (
            'OpenID identifier="http://steamcommunity.com/openid"'
        )
        return response

    userkey = getuserkey(user['id'])

    if option == 'add':
        index = int(request.forms.get('index'))
        quality = int(request.forms.get('quality'))

        if (await store.sismember('items:indexes', index) and
                quality in tf2api.getallqualities()):

            if len(user['wishlist']) < 100:
                user['wishlist'].append({'index': index,
                                         'quality': quality})
                await store.hset(userkey, 'wishlist', user['wishlist'])

                return 'Added'

    elif option == 'remove':
        i = int(request.forms.get('i'))

        if 0 <= i < len(user['wishlist']):
            del user['wishlist'][i]
            await store.hset(userkey, 'wishlist', user['wishlist'])

            return 'Removed'


@get('/suggest')
@sync
async def suggest():
    query = request.query.q

    allsuggestions = await store.get('items:suggestions')
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
@sync
async def user(urltype, steamid):
    path = urlparse(request.url).path

    currentuser = await getcurrentuser(request)
    if currentuser and currentuser['url'] == path:
        user = currentuser
    else:
        user = await getuser(steamid, urltype)

    if user:
        if user['url'] != path:
            return redirect(user['url'])

        items = await getitems(item['index'] for item in user['wishlist'])

        for i, item in enumerate(items):
            item.update({'i': i})
            item.update(user['wishlist'][i])

    else:
        abort(404)

    return await render('user.html',
                        user=user,
                        items=items)


@get('/login')
def login():
    sid = b64encode(os.urandom(16)).decode()
    session = {'sid': sid}
    expires = datetime.now() + session_age
    response.set_cookie('sid', sid, expires=expires,
                        httponly=True, secure=True)

    c = consumer.Consumer(session, None)
    a = c.begin('http://steamcommunity.com/openid')
    url = a.redirectURL(config.homepage, login_verify_url)

    return redirect(url)


@get('/login/verify')
@sync
async def login_verify():
    sid = request.get_cookie('sid')
    session = {'sid': sid}

    c = consumer.Consumer(session, None)
    info = c.complete(request.query, login_verify_url)

    if info.status == consumer.SUCCESS:
        steamid = request.query['openid.claimed_id'].split('/')[-1]
        user = await getuser(steamid, create=True)
        await store.setex(getsessionkey(sid), int(session_age.total_seconds()),
                          user['id'])

    return redirect('/')


@get('/sitemap.xml')
@sync
async def sitemap():
    response.set_header('Content-Type', 'application/xml;charset=UTF-8')
    return await store.get('sitemap')


@get('/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static')


@error(404)
@sync
async def error404(exception):
    return await render('error.html', message='Page Not Found')


@error(500)
@sync
async def error500(exception):
    logger.exception(exception)
    return await render('error.html', message='Server Error')


async def render(template, **params):
    """Render HTML template"""
    template = jinja_env.get_template(template)
    return await template.render_async(params)


def tojson(*args, **kwargs):
    response.set_header('Content-Type', 'application/json;charset=UTF-8')
    return rapidjson.dumps(*args, **kwargs)


async def getresults(classes, tags):
    key = getsearchkey(classes, tags)
    multikey = getsearchkey(classes, tags, 'Multi')
    allkey = getsearchkey(classes, tags, 'All')

    title = tf2search.getclasstagtitle(classes, tags)

    keys = (key, multikey, allkey)
    titles = (title, 'Multi-Class Items', 'All-Class Items')

    if not await store.exists(key) and not await store.exists(allkey):
        classeskey = 'temp:classes'
        tagskey = 'temp:tags'
        remove = []

        pipe = store.multi_exec()

        classkeys = [getclasskey(class_) for class_ in classes] or ['items']
        pipe.sunionstore(classeskey, *classkeys)

        # Get only the specified weapon types
        if 'weapon' in tags and not tags.isdisjoint(tf2api.getweapontags()):
            tags.remove('weapon')
            remove.append(gettagkey('token'))

        tagkeys = [gettagkey(tag) for tag in tags] or ['items']
        pipe.sunionstore(tagskey, *tagkeys)

        # Hide medals if not explicitly searching for them
        if 'tournament' not in tags:
            remove.append(gettagkey('tournament'))

        if remove:
            pipe.sdiffstore(tagskey, *([tagskey] + remove))

        pipe.sinterstore(key, classeskey, tagskey)
        pipe.sinterstore(multikey, key, getclasskey(multi=True))
        pipe.sinterstore(allkey, tagskey, getclasskey())
        pipe.sdiffstore(key, key, multikey, allkey)

        pipe.delete(classeskey)
        pipe.delete(tagskey)

        for k in keys:
            pipe.sort(k, store=k)
            pipe.expire(k, 3600)

        await pipe.execute()

    async def getkeys(key):
        return [getitemkey(k) for k in await store.lrange(key, 0, -1)]

    results = []
    for title, key in zip(titles, keys):
        itemkeys = await getkeys(key)
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


async def getcurrentuser(request):
    user = None

    sid = request.get_cookie('sid')

    if sid:
        userid = await store.get(getsessionkey(sid))
        if userid:
            user = await getuser(userid)

    return user


async def getuser(steamid, urltype='profiles', create=False):
    if urltype == 'id':
        steamid = await tf2api.resolvevanityurl(config.apikey, steamid)

    userkey = getuserkey(steamid)
    user = await store.hgetall(userkey)

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
            steamuser = await tf2api.getplayersummary(config.apikey, steamid)

        except URLError:
            # Postpone update if this is not a new user
            if create:
                raise
            return user

        user['name'] = steamuser['personaname']
        # Remove trailing slash and parse url
        user['url'] = urlparse(steamuser['profileurl'].rstrip('/')).path
        user['avatar'] = steamuser['avatar']
        user['state'] = ('Online' if steamuser['personastate'] != 0 else
                         'Offline')

        if 'gameid' in steamuser:
            user['state'] = 'In-Game'

        if 'wishlist' not in user:
            user['wishlist'] = []

        user['lastupdate'] = datetime.now().timestamp()

        await store.hmset_dict(userkey, user)
        await store.sadd('users', user['id'])

    return user


def getuserkey(uid):
    return 'user:{}'.format(uid)


def getsessionkey(sid):
    return 'session:{}'.format(sid)


async def getitems(indexes):
    return await store.hgetall([getitemkey(index) for index in indexes])


async def getitem(index):
    return await store.hgetall(getitemkey(index))


async def getitembyslug(slug):
    index = await store.hget('items:slugs', slug)
    return await getitem(index) if index is not None else None


def getitemkey(index):
    return 'item:{}'.format(index)


init()

if __name__ == '__main__':
    run(host='localhost', port=8000, reloader=True)

app = default_app()
