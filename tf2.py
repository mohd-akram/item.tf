
# coding: utf-8

"""This module contains all the page handlers and caching mechanisms."""
import os
import time
import random
import pickle
import logging
from itertools import izip
from datetime import datetime, timedelta
from httplib import HTTPException
from xml.dom.minidom import getDOMImplementation

from lib import cloudstorage as gcs

from google.appengine.api import memcache, users, taskqueue, app_identity
from google.appengine.ext import ndb

import tf2api
import tf2search

import config
from handler import Handler


def getfilename(filename):
    bucket_name = os.environ.get('BUCKET_NAME',
                                 app_identity.get_default_gcs_bucket_name())

    return '/{}/{}'.format(bucket_name, filename)


def populatecache(data=None):
    if data is None:
        try:
            gcs_file = gcs.open(getfilename(config.datafile))
        except gcs.NotFoundError:
            taskqueue.add(url='/cache/update', method='GET')
        else:
            data = pickle.loads(gcs_file.read())
            memcache.set_multi(data)
            gcs_file.close()
    else:
        memcache.set_multi(data)


def updatecache():
    t0 = time.time()

    tf2info = tf2search.gettf2info(config.apikey,
                                   config.backpackkey, config.tradekey,
                                   config.blueprintsfile)

    itemsdict = ItemsDict(tf2search.getitemsdict(tf2info, 3))

    newitems = [itemsdict[index] for index in tf2info.newstoreprices]

    nametoindexmap = {}
    itemindexes = set()
    suggestions = [[], [], []]

    sitemap = Sitemap()
    sitemap.add(config.homepage)

    for name, item in tf2info.itemsbyname.iteritems():
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

    t1 = time.time()

    data = {'itemsdict0': itemsdict.dicts[0],
            'itemsdict1': itemsdict.dicts[1],
            'itemsdict2': itemsdict.dicts[2],
            'itemsets': tf2info.itemsets,
            'bundles': tf2info.bundles,
            'nametoindexmap': nametoindexmap,
            'itemindexes': itemindexes,
            'newitems': newitems,
            'suggestions': suggestions,
            'sitemap': sitemap.toxml(),
            'lastupdated': t1}

    gcs_file = gcs.open(getfilename(config.datafile), 'w')
    gcs_file.write(pickle.dumps(data))
    gcs_file.close()

    populatecache(data)

    logging.debug('Updated Cache. Time taken: {} seconds'.format(t1 - t0))


def getfromcache(key):
    if key == 'itemsdict':
        dicts = memcache.get_multi(['0', '1', '2'], 'itemsdict')
        try:
            value = ItemsDict([dicts['0'], dicts['1'], dicts['2']])
        except KeyError:
            value = None
    else:
        value = memcache.get(key)

    if value is None:
        logging.debug("Could not find key '{}'. Populating cache.".format(key))
        if taskqueue.Queue().fetch_statistics().tasks == 0:
            taskqueue.add(url='/cache/populate', method='GET')

    return value


def getsteamid(openiduser):
    return openiduser.nickname().split('/')[-1] if openiduser else None


def getuser(steamid, urltype='profiles', create=False):
    if urltype == 'id':
        steamid = tf2api.resolvevanityurl(config.apikey, steamid)

    user = User.get_by_id(steamid)

    if user:
        create = False
        needsupdate = (datetime.now() - user.lastupdate) > timedelta(minutes=3)
    else:
        if not create:
            return
        user = User(id=steamid)

    if create or needsupdate:
        try:
            steamuser = tf2api.getplayersummary(config.apikey, steamid)

        except HTTPException:
            # Postpone update if this is not a new user
            if create:
                raise
            return user

        user.name = steamuser['personaname']
        user.url = steamuser['profileurl'].split('/')[-2]
        user.avatar = steamuser['avatar']
        user.state = 'Online' if steamuser['personastate'] != 0 else 'Offline'

        if 'gameid' in steamuser:
            user.state = 'In-Game'

        user.put()

    return user


class TF2Handler(Handler):
    """Homepage handler"""
    def get(self):
        t0 = getfromcache('lastupdated')
        lastupdated = int(time.time() - t0) / 60

        user = None

        openidurl = 'http://steamcommunity.com/openid'
        openiduser = users.get_current_user()

        if openiduser:
            steamid = getsteamid(openiduser)
            user = getuser(steamid, create=True)

            self.response.set_cookie('steam_id', steamid)
        else:
            self.response.delete_cookie('steam_id')

        newitems = getfromcache('newitems')
        if len(newitems) > 5:
            newitems = random.sample(newitems, 5)

        self.render('tf2.html',
                    homepage=config.homepage,
                    user=user,
                    loginurl=users.create_login_url('/', None, openidurl),
                    tags=tf2api.getalltags(),
                    newitems=newitems,
                    message=random.choice(config.messages),
                    lastupdated=lastupdated)


class TF2SearchHandler(Handler):
    def get(self, is_json):
        query = self.request.get('q')

        if not query:
            self.redirect('/')

        elif query == 'random':
            itemindexes = getfromcache('itemindexes')
            return self.redirect(
                # random.choice does not support sets
                '/{}'.format(random.choice(tuple(itemindexes))))

        nametoindexmap = getfromcache('nametoindexmap')

        if query in nametoindexmap:
            return self.redirect('/{}'.format(nametoindexmap[query]))

        itemsdict = getfromcache('itemsdict')
        itemsets = getfromcache('itemsets')
        bundles = getfromcache('bundles')

        pricesource = self.request.cookies.get('price_source')

        sources = ('backpack.tf', 'trade.tf')
        if pricesource not in sources:
            pricesource = sources[0]

        t0 = time.time()
        results = tf2search.search(query, itemsdict, nametoindexmap,
                                   itemsets, bundles, pricesource)
        t1 = time.time()

        if is_json:
            self.write_json(results)
        else:
            self.render('tf2results.html',
                        query=query,
                        results=results,
                        count=sum(len(result['items']) for result in results),
                        time=round(t1 - t0, 3))


class TF2SuggestHandler(Handler):
    """OpenSearch suggestions handler"""
    def get(self):
        query = self.request.get('q')

        allsuggestions = getfromcache('suggestions')
        suggestions = [query, [], [], []]

        if query:
            for name, desc, path in izip(*allsuggestions):
                foldedname = tf2search.foldaccents(name)

                if query in foldedname or query in foldedname.lower():
                    suggestions[1].append(name)
                    suggestions[2].append(desc)
                    suggestions[3].append(path)
        else:
            suggestions[1:] = allsuggestions

        self.write_json(suggestions)


class TF2UserHandler(Handler):
    def get(self, urltype, steamid):
        usersteamid = getsteamid(users.get_current_user())
        # Avoid a Steam API call if the user is visiting his own page
        if usersteamid:
            user = getuser(usersteamid)
            if urltype == 'id':
                if steamid == usersteamid:
                    user = None
                if user and steamid == user.url:
                    steamid = usersteamid

        if steamid != usersteamid:
            user = getuser(steamid, urltype)

        if user:
            if urltype == 'profiles' and user.key.id() != user.url:
                return self.redirect('/id/{}'.format(user.url))

            itemsdict = getfromcache('itemsdict')
            items = []

            wishlist = user.wishlist

            for i, item in enumerate(wishlist):
                itemdict = itemsdict[item['index']].copy()
                item.update({'i': i})
                itemdict.update(item)
                items.append(itemdict)

        else:
            return self.redirect('/')

        self.render('tf2user.html',
                    user=user,
                    wishlist=user.wishlist,
                    items=items)


class TF2WishlistHandler(Handler):
    def post(self, option):
        openiduser = users.get_current_user()

        if not openiduser:
            self.response.headers['WWW-Authenticate'] = (
                'OpenID identifier="http://steamcommunity.com/openid"')
            return self.response.set_status(401)

        steamid = getsteamid(openiduser)
        user = getuser(steamid)

        if option == 'add':
            index = int(self.request.get('index'))
            quality = int(self.request.get('quality'))

            if (index in getfromcache('itemindexes') and
                    quality in tf2api.getallqualities()):

                user.wishlist.append({'index': index,
                                      'quality': quality})
                user.put()

                self.write('Added')

        elif option == 'remove':
            i = int(self.request.get('i'))

            del user.wishlist[i]
            user.put()

            self.write('Removed')


class TF2ItemHandler(Handler):
    def get(self, defindex, is_json):
        itemsdict = getfromcache('itemsdict')
        index = int(defindex)

        if index in itemsdict:
            itemdict = itemsdict[index]
        else:
            return self.redirect('/')

        if is_json:
            self.write_json(itemdict, indent=2)
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
        if option == 'populate':
            populatecache()
            self.write('Cache Populated')
        elif option == 'update':
            updatecache()
            self.write('Cache Updated')
        elif option == 'flush':
            memcache.flush_all()
            self.write('Cache Flushed')


class RedirectHandler(Handler):
    def get(self, *args):
        self.redirect(config.homepage + self.request.path_qs, True)


class User(ndb.Model):
    name = ndb.StringProperty('n')
    url = ndb.StringProperty('u')
    avatar = ndb.StringProperty('a')
    state = ndb.StringProperty('s')
    wishlist = ndb.PickleProperty('w', default=[])

    lastupdate = ndb.DateTimeProperty('t', auto_now=True)


class ItemsDict:
    def __init__(self, dicts):
        self.dicts = dicts

    def __contains__(self, key):
        return any(key in dict_ for dict_ in self.dicts)

    def __len__(self):
        return sum(len(dict_) for dict_ in self.dicts)

    def __getitem__(self, key):
        for dict_ in self.dicts:
            if key in dict_:
                return dict_[key]

    def __iter__(self):
        for dict_ in self.dicts:
            for key in dict_:
                yield key

    def itervalues(self):
        for dict_ in self.dicts:
            for key in dict_:
                yield dict_[key]

    def values(self):
        return list(self.itervalues())


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
