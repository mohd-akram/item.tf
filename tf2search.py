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

from tf2api import (getitems, getattributes, getparticleeffects,
                    getalltags, getallclasses,
                    getitemattributes, getitemclasses, getitemtags,
                    getstoreprice, getmarketprice)

def splitspecial(string):
    """Splits a string at special characters"""
    return [i for i in re.split(r'\W+',string) if i]

def getclass(word):
    word = word.capitalize()
    for name,aliases in getallclasses().items():
        if word == name or word in aliases:
            return name

def gettag(word):
    weapon = ['wep','weap']
    tags = getalltags()
    for tag in tags:
        if word in weapon or word in [i+'s' for i in weapon]:
            return 'weapon'
        elif word == tag or word == tag+'s':
            return tag

def parseblueprints(blueprints,itemsbyname):
    url = '/images/items/'
    localrepl = {'Any Class Token':'class_token.png',
                 'Any Slot Token':'slot_token.png',
                 'Any Token':'token.png',
                 'Any Primary Weapon':'primary.png',
                 'Any Secondary Weapon':'secondary.png',
                 'Any Melee Weapon':'melee.png',
                 'Any Spy Watch':'pda2.png'}

    repl = {"Any Santa's Little Accomplice Weapon":"Santa's Little Accomplice Bundle",
            "Any Burned Item":"Burned Banana Peel"}

    polyweps = {'Pyro':"The Gas Jockey's Gear",
                'Spy':"The Saharan Spy",
                'Soldier':"The Tank Buster",
                'Sniper':"The Croc-o-Style Kit",
                'Scout':"The Special Delivery"}

    for class_ in getallclasses():
        repl['Any {} Weapon'.format(class_)] = '{} Starter Pack'.format(class_)

    for class_,name in polyweps.items():
        repl['Any Polycount {} Bundle Weapon'.format(class_)] = name

    for i in ['Victory','Moonman','Brainiac']:
        pack = "Dr. Grordbort's {} Pack".format(i)
        repl["Any {} Weapon".format(pack)] = pack

    blueprintsdict = defaultdict(list)
    for b in blueprints:
        required = blueprints[b][0]
        results = blueprints[b][1]

        for name in results:
            if name in itemsbyname:
                index = itemsbyname[name]['defindex']
                chance = int(round(100.0/len(results)))

                blueprintlist = []

                for i in OrderedDict.fromkeys(required):
                    blueprintdict = {}

                    if i in localrepl:
                        image = url + localrepl[i]

                    elif i in repl:
                        image = itemsbyname[repl[i]]['image_url']

                    elif i in itemsbyname:
                        item = itemsbyname[i]
                        image = item['image_url']

                        blueprintdict['index'] = item['defindex']

                    else:
                        image = '/images/items/whatsthis.png'

                    blueprintdict['name'] = i
                    blueprintdict['image'] = image
                    blueprintdict['count'] = required.count(i)

                    blueprintlist.append(blueprintdict)

                blueprintsdict[index].append({'chance':chance,'required':blueprintlist})

    return blueprintsdict

def createitemdict(item, attributes, effects, blueprints, storeprices, marketprices):
    """Takes a TF2 item and returns a custom dict with a limited number of
    keys that are used for search"""
    classes = getitemclasses(item)

    description = ''
    if 'item_description' in item:
        description = item['item_description']

    attributes = getitemattributes(item, attributes, effects)
    storeprice = getstoreprice(item, storeprices)
    marketprice = getmarketprice(item, marketprices)
    tags = getitemtags(item)
    blueprint = sorted(blueprints[item['defindex']],reverse=True) # Sort by chance

    itemdict = {'name':item['item_name'],
                'image':item['image_url'],
                'image_large':item['image_url_large'],
                'classes':classes,
                'tags':tags,
                'index':item['defindex'],
                'description':description,
                'attributes':attributes,
                'storeprice':storeprice,
                'marketprice':marketprice,
                'blueprints':blueprint}

    if 'paint' in tags:
        paintvalue = str(int(item['attributes'][1]['value']))
        # Ignore Paint Tool
        if paintvalue != '1':
            itemdict['image'] = itemdict['image_large'] = '/images/paints/Paint_Can_{}.png'.format(paintvalue)

    return itemdict

def getitemsdict(schema, blueprints, storeprices, marketprices):
    """Returns an ordered dictionary with index as key and an itemdict as value"""
    itemsdict = OrderedDict()
    items = getitems(schema)
    attributes = getattributes(schema)
    effects = getparticleeffects(schema)
    for idx in items:
        itemdict = createitemdict(items[idx],attributes,effects,blueprints,storeprices,marketprices)
        itemsdict[idx] = itemdict

    return itemsdict

def parseinput(query):
    querylist = [i for i in splitspecial(query.lower()) if i not in ['the','a','of','s']]

    classes = []
    tags = []
    for word in querylist:
        class_ = getclass(word)
        tag = gettag(word)

        if class_:
            classes.append(class_)
        if tag:
            tags.append(tag)

    if (len(tags) + len(classes)) != len(querylist):
        classes = tags = []

    return {'querylist':querylist,'classes':classes,'tags':tags}

def search(query, itemsdict):
    """This method parses the result obtained from parseInput and gets all the
    items that match this result. It returns a dict with three keys - classitems,
    allclassitems and searchitems. If the user's query did not match any class
    or tag, a regular search is done and the searchitems is populated with
    the result. If it did match a class and/or item tag, the results are divided
    into specific class items (classitems) and all-class items (allclassitems)"""
    classitems = []
    allclassitems = []
    searchitems = []
    names = []

    result = parseinput(query)
    classes = result['classes']
    tags = result['tags']

    querylist = result['querylist']

    if classes or tags:
        for itemdict in itemsdict.values():
            itemclasses = itemdict['classes']

            isclassmatch = not set(itemclasses).isdisjoint(classes) or not itemclasses
            istagmatch = set(tags).issubset(itemdict['tags'])

            if (isclassmatch or not classes) and (istagmatch or not tags):
                name = itemdict['name']
                index = itemdict['index']
                if itemdict['image'] and (index<496 or (512<index<680) or (698<index<8000)) and name not in names:
                    if len(itemclasses)==1 or not classes:
                        classitems.append(itemdict)
                    else:
                        allclassitems.append(itemdict)
                    names.append(name)
    else:
        if querylist == ['all']:
            searchitems = itemsdict.values()
        else:
            for itemdict in itemsdict.values():
                itemname = splitspecial(itemdict['name'].lower())

                match = not set(itemname).isdisjoint(querylist)

                if (match and itemdict['image'] and itemname not in names):
                    searchitems.append(itemdict)
                    names.append(itemname)

            searchitems = getsorteditemlist(searchitems,querylist)

    return {'classitems':classitems, 'allclassitems':allclassitems, 'searchitems':searchitems}

def getsorteditemlist(itemlist, querylist):
    indexlist = []

    for itemdict in itemlist:
        name = itemdict['name'].lower()
        intersectionlength = len(set(querylist).intersection(splitspecial(name)))
        indexlist.append(intersectionlength)

    return [itemlist for (indexlist,itemlist) in sorted(zip(indexlist,itemlist),reverse=True)]