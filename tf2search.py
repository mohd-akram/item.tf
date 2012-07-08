"""A module for parsing a query and searching for TF2 items
It supports class based search, eg: 'engineer hats'
It also supports alias based search, eg: 'engi hats'
Regular search, eg: 'Meet the Medic'
Requires TF2 API module to get items and prices.

Usage:
    items = search('engi medic hats', itemsdict)

Note: You must provide your own image URLs for the paint cans.
      Replace the relative URL in createitemdict.
"""
import re
import logging
from collections import defaultdict, OrderedDict

from tf2api import (getallitemtypes, gettf2classes, getstoreprice,
                    getmarketprice, getitemclasses, getitemtags,
                    getduplicates, ispaint)

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
    weapon = ['wep','weap']
    itemtypes = getallitemtypes()
    for itemtype in itemtypes:
        if word in weapon or word in [i+'s' for i in weapon]:
            return 'weapon'
        elif word == itemtype or word == itemtype+'s':
            return itemtype

def parseblueprints(blueprints,itemsbyname):
    url = '/images/items/'
    repl = {'Any Class Token':'class_token.png',
            'Any Slot Token':'slot_token.png',
            'Any Token':'token.png',
            'Any Primary Weapon':'primary.png',
            'Any Secondary Weapon':'secondary.png',
            'Any Melee Weapon':'melee.png',
            'Any Spy Watch':'watch.png'}

    blueprintsdict = defaultdict(list)
    for i in blueprints:
        required = blueprints[i][0]
        results = set(blueprints[i][1])

        for name in results:
            if name in itemsbyname:
                index = itemsbyname[name]['defindex']
                chance = int(100.0/len(results))

                blueprintlist = []

                for j in required:
                    # Some required items don't have an index
                    index2 = ''
                    image = ''
                    anyclasswep = re.match(r'Any (\w+) Weapon',j)

                    if anyclasswep:
                        tf2class = anyclasswep.group(1)
                        if tf2class not in ['Primary','Secondary']:
                            image = url + '{}_icon.png'.format(anyclasswep.group(1))

                    if j in repl:
                        image = url + repl[j]

                    if j == 'Any Burned Item':
                        image = itemsbyname['Burned Banana Peel']['image_url']

                    if j in itemsbyname:
                        item = itemsbyname[j]
                        image = item['image_url']
                        index2 = item['defindex']

                    blueprintdict = {'name':j,'image':image,'index':index2}
                    blueprintlist.append(blueprintdict)

                blueprintsdict[index].append((blueprintlist,chance))
    return blueprintsdict

def createitemdict(item, storeprices, marketprices, blueprints):
    """Takes a TF2 item and returns a custom dict with a limited number of
    keys that are used for search"""
    classes = getitemclasses(item)

    storeprice = getstoreprice(item, storeprices)
    marketprice = getmarketprice(item, marketprices)
    tags = getitemtags(item)
    blueprint = blueprints[item['defindex']]

    itemdict = {'name':item['item_name'],
                'image':item['image_url'],
                'image_large':item['image_url_large'],
                'classes':classes,
                'tags':tags,
                'index':item['defindex'],
                'storeprice':storeprice,
                'marketprice':marketprice,
                'blueprint':blueprint}

    if ispaint(item):
        paintvalue = str(int(item['attributes'][1]['value']))
        # Ignore Paint Tool
        if paintvalue != '1':
            itemdict['image'] = itemdict['image_large'] = '/images/paints/Paint_Can_{}.png'.format(paintvalue)

    return itemdict

def getitemsdict(items, storeprices, marketprices, blueprints):
    """Returns an ordered dictionary with index as key and an itemdict as value"""
    itemsdict = OrderedDict()

    for idx in items:
        itemdict = createitemdict(items[idx],storeprices,marketprices,blueprints)
        itemsdict[idx] = itemdict

    return itemsdict

def parseinput(query):
    query = query.lower()
    querylist = splitspecial(query)
    classes = []
    types = []
    for idx,word in enumerate(querylist):
        tf2class = getclass(word)
        itemtype = getitemtype(word)

        # Originally a fix when searching for "Meet the Medic"
        # It ignores any class names if they are at the end or not preceded by
        # another class name
        if tf2class and (idx==0 or getclass(querylist[idx-1])):
            classes.append(tf2class)
        if itemtype:
            types.append(itemtype)

    querylist = [i for i in querylist if i not in ['the','a','of']]

    result = {'querylist':querylist,'classes':classes,'types':types}
    return result

def getresultitems(result, itemsdict):
    """This method parses the result obtained from parseInput and gets all the
    items that match this result. It returns a dict with three keys - classitems,
    allclassitems and searchitems. If the user's query did not match any class
    or itemtype, a regular search is done and the searchitems is populated with
    the result. If it did match a class and/or item type, the results are divided
    into specific class items (classitems) and all-class items (allclassitems)"""
    classitems = []
    allclassitems = []
    searchitems = []
    # Exclude some items from search results
    noimages = [122,123,124,472,495,2061,2066,2067,2068]
    duplicates = getduplicates()
    exclusions = duplicates + noimages + [5023]

    classes = result['classes']
    types = result['types']

    querylist = result['querylist']

    if classes or types:
        for idx in itemsdict:
            itemdict = itemsdict[idx]
            itemclasses = itemdict['classes']

            isclassmatch = not set(itemclasses).isdisjoint(classes) or not itemclasses
            istypematch = not set(types).isdisjoint(itemdict['tags'])

            if (isclassmatch or not classes) and (istypematch or not types):
                itemdict = itemsdict[idx]
                if itemdict['index'] not in exclusions:
                    if len(itemclasses)==1 or not classes:
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

def search(query, itemsdict):
    result = parseinput(query)
    return getresultitems(result, itemsdict)