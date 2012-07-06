"""A module for parsing a query and searching for TF2 items
It supports class based search, eg: 'engineer hats'
It also supports alias based search, eg: 'engi hats'
Regular search, eg: 'Meet the Medic'
Requires TF2 API module to get items and prices.

Usage:
    items = search('engi medic hats', items, itemsdict)

Note: You must provide your own image URLs for the paint cans.
      Replace the relative URL in createitemdict.
"""
import re
import logging
from collections import OrderedDict

from tf2api import (getitemtypes, gettf2classes, getstoreprice,
                    getmarketprice, getitemclasses, isweapon,
                    ishat, ismisc, isaction, istaunt, istool, ispaint)

def splitspecial(string):
    """Splits a string at special characters"""
    regex = re.compile(r'\W+')
    return regex.split(string)

def getclass(word):
    word = word.capitalize()
    for tf2class in gettf2classes():
        if word == tf2class['name'] or word in tf2class['aliases']:
            return tf2class['name']

def getitemtype(word):
    itemtypes = getitemtypes() + ['weap','wep']
    for itemtype in itemtypes:
        if word == itemtype or word == itemtype+'s':
            return itemtype

def createitemdict(item, storeprices, marketprices):
    """Takes a TF2 item and returns a custom dict with a limited number of
    keys that are used for search"""
    if 'used_by_classes' in item:
        classes = item['used_by_classes']
    else:
        classes = []

    storeprice = getstoreprice(item, storeprices)
    marketprice = getmarketprice(item, marketprices)

    itemdict = {'name':item['item_name'],
                'image':item['image_url'],
                'image_large':item['image_url_large'],
                'classes':classes,
                'index':item['defindex'],
                'storeprice':storeprice,
                'marketprice':marketprice
                }

    if 'tool' in item:
        if ispaint(item):
            paintvalue = str(int(item['attributes'][1]['value']))
            # Ignore Paint Tool
            if paintvalue != '1':
                itemdict['image'] = itemdict['image_large'] = '/images/paints/Paint_Can_{}.png'.format(paintvalue)

    return itemdict

def getitemsdict(items, storeprices, marketprices):
    """Returns an ordered dictionary with index as key and an itemdict as value"""
    itemsdict = OrderedDict()
    for idx in items:
        itemdict = createitemdict(items[idx],storeprices,marketprices)
        itemsdict[idx] = itemdict

    return itemsdict

def parseinput(query):
    query = query.lower()
    querylist = splitspecial(query)
    classes = []
    itemtypes = []
    for idx,word in enumerate(querylist):
        tf2class = getclass(word)
        itemtype = getitemtype(word)

        if tf2class and (idx==0 or getclass(querylist[idx-1])) :
            classes.append(tf2class)
        if itemtype:
            itemtypes.append(itemtype)

    querylist = [i for i in querylist if i not in ['the','a','of']]

    result = {'querylist':querylist,'classes':classes,'itemtypes':itemtypes}
    return result

def getresultitems(result, items, itemsdict):
    """This method parses the result obtained from parseInput and gets all the
    items that match this result. It returns a dict with three keys - classitems,
    allclassitems and searchitems. If the user's query did not match any class
    or itemtype, a regular search is done and the searchitems is populated with
    the result. If it did match a class and/or item type, the results are divided
    into specific class items (classitems) and all-class items (allclassitems)"""
    classitems = []
    allclassitems = []
    searchitems = []
    exclusions = [122,123,124,472,495,2061,2066,2067,2068,5023]

    classes = result['classes']
    itemtypes = result['itemtypes']

    querylist = result['querylist']

    if classes or itemtypes:
        for idx in items:
            item = items[idx]
            itemclasses = getitemclasses(item)

            isclassmatch = not set(itemclasses).isdisjoint(classes) or not itemclasses

            isweaponmatch = not set(itemtypes).isdisjoint(['weapon','weap','wep']) and isweapon(item)
            istoolmatch = 'tool' in itemtypes and istool(item)
            ispaintmatch = 'paint' in itemtypes and ispaint(item)
            ishatmatch = 'hat' in itemtypes and ishat(item)
            ismiscmatch = 'misc' in itemtypes and ismisc(item)
            isactionmatch = 'action' in itemtypes and isaction(item)
            istauntmatch = 'taunt' in itemtypes and istaunt(item)

            if ((isclassmatch or not classes) and
            (isweaponmatch
            or ishatmatch
            or ismiscmatch
            or isactionmatch
            or istoolmatch
            or istauntmatch
            or ispaintmatch
            or not itemtypes)):
                itemdict = itemsdict[idx]
                if itemdict['index'] not in exclusions:
                    if len(itemclasses)==1:
                        classitems.append(itemdict)
                    else:
                        allclassitems.append(itemdict)
    else:
        isgetall = querylist == ['all']
        for idx in itemsdict:
            itemdict = itemsdict[idx]
            itemname = splitspecial(itemdict['name'].lower())

            match = not set(itemname).isdisjoint(querylist)

            if (match and itemdict['index'] not in exclusions) or isgetall:
                searchitems.append(itemdict)

        # Sort search items
        if not isgetall:
            searchitems = getsorteditemlist(searchitems,querylist)

    resultitemsdict = {'classitems':classitems, 'allclassitems':allclassitems, 'searchitems':searchitems}

    return resultitemsdict

def getsorteditemlist(itemlist, querylist):
    indexlist = []
    for itemdict in itemlist:
        name = itemdict['name'].lower().replace('!','')
        intersectionlength = len(set(querylist).intersection(name.split()))
        indexlist.append(intersectionlength)

    sortedlist =[itemlist for (indexlist,itemlist) in sorted(zip(indexlist,itemlist),reverse=True)]
    return sortedlist

def search(query, items, itemsdict):
    result = parseinput(query)
    return getresultitems(result, items, itemsdict)