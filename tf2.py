
# coding: utf-8

"""This module contains all the page handlers and caching mechanisms."""
import json
import logging
import time
import random
from itertools import izip
from datetime import datetime, timedelta
from httplib import HTTPException
from xml.dom.minidom import getDOMImplementation

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

import tf2api
import tf2search

import config
from handler import Handler


def updatecache():
    t0 = time.time()

    tf2info = tf2search.gettf2info(config.apikey, config.backpackkey,
                                   config.blueprintsfile)
    itemsdict = ItemsDict(tf2search.getitemsdict(tf2info, 2))

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

            path = '{0}/item/{1}'.format(config.homepage, index)

            suggestions[0].append(name)
            suggestions[1].append('{} - {}'.format(
                ', '.join(itemdict['classes']), ', '.join(itemdict['tags'])))
            suggestions[2].append(path)

            sitemap.add(path)

    memcache.set_multi({'itemsdict0': itemsdict.dicts[0],
                        'itemsdict1': itemsdict.dicts[1],
                        'itemsets': tf2info.itemsets,
                        'bundles': tf2info.bundles,
                        'nametoindexmap': nametoindexmap,
                        'itemindexes': itemindexes,
                        'newitems': newitems,
                        'suggestions': suggestions,
                        'sitemap': sitemap.toxml()})
    t1 = time.time()

    memcache.set('lastupdated', t1)
    logging.debug('Updated Cache. Time taken: {} seconds'.format(t1 - t0))


def getfromcache(key):
    if key == 'itemsdict':
        dicts = memcache.get_multi(['0', '1'], 'itemsdict')
        try:
            value = ItemsDict([dicts['0'], dicts['1']])
        except KeyError:
            value = None
    else:
        value = memcache.get(key)

    if not value:
        logging.debug("Could not find key '{}'. Updating cache.".format(key))
        updatecache()
        return getfromcache(key)

    return value


def getsteamid(openiduser):
    return openiduser.nickname().split('/')[-1] if openiduser else None


def getuser(steamid, create=False):
    user = User.get_by_id(steamid)

    if user:
        needsupdate = (datetime.now() - user.lastupdate) > timedelta(minutes=3)
    else:
        if not create:
            return None
        user = User(id=steamid)
        needsupdate = True

    if needsupdate:
        try:
            steamuser = tf2api.getplayersummary(config.apikey, steamid)

        except HTTPException:
            # Postpone update if this is not a new user
            if not create:
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
        if self.request.host.endswith('appspot.com'):
            return self.redirect(config.homepage, True)

        t0 = getfromcache('lastupdated')
        lastupdated = int(time.time() - t0) / 60

        user = None

        openidurl = 'http://steamcommunity.com/openid'
        openiduser = users.get_current_user()

        if openiduser:
            steamid = getsteamid(openiduser)
            user = getuser(steamid, True)

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
    def get(self):
        query = self.request.get('q')

        if query:
            if query == 'random':
                itemindexes = getfromcache('itemindexes')
                return self.redirect(
                    # random.choice does not support sets
                    '/item/{}'.format(random.choice(tuple(itemindexes))))

            nametoindexmap = getfromcache('nametoindexmap')

            if query in nametoindexmap:
                return self.redirect('/item/{}'.format(nametoindexmap[query]))

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
                        otheritems=sorted(results['otheritems'].iteritems(),
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

        self.response.headers['Content-Type'] = ('application/json;'
                                                 'charset=UTF-8')
        self.write(json.dumps(suggestions))


class TF2UserHandler(Handler):
    def get(self, steamid):
        usersteamid = getsteamid(users.get_current_user())
        # Avoid a Steam API call if the user is visiting his own page
        if usersteamid:
            user = getuser(usersteamid)
            # User is visiting his own page
            if steamid in (usersteamid, user.url):
                steamid = usersteamid

        if steamid != usersteamid:
            steamid = (tf2api.resolvevanityurl(config.apikey, steamid) or
                       steamid)
            user = getuser(steamid)

        if user:
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
