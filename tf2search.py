"""A module for parsing a query and searching for TF2 items
It supports class based search, eg: 'engineer hats'
It also supports alias based search, eg: 'engi hats'
Regular search, eg: 'Meet the Medic'
Slot search, eg: 'primary weps'
Set search, eg: 'the saharan spy set'
Requires TF2 API module to get items and prices.

Usage:
    items = search('engi medic hats', itemsdict, itemsbyname, itemsets)

Note: You must provide your own image URLs for the paint cans.
      Replace the relative URL in createitemdict.
"""
import re
import logging
from collections import defaultdict, OrderedDict

from tf2api import (getitems, getattributes, getparticleeffects, getitemsets,
                    getalltags, getallclasses, getweapontags,
                    getitemattributes, getitemclasses, getitemtags,
                    getstoreprice, getmarketprice)

def splitspecial(string):
    """Split a string at special characters"""
    return [i for i in re.split(r'\W+',string.lower()) if i]

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

def parseblueprints(blueprints, itemsbyname):
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

    polyweps = ["The Gas Jockey's Gear","The Saharan Spy","The Tank Buster",
                "The Croc-o-Style Kit","The Special Delivery"]

    for class_ in getallclasses():
        repl['Any {} Weapon'.format(class_)] = '{} Starter Pack'.format(class_)

    for name in polyweps:
        repl['Any {} Weapon'.format(name)] = name

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

def createitemdict(item, attributes, effects, itemsets, bundles, blueprints, storeprices, marketprices):
    """Take a TF2 item and return a custom dict with a limited number of
    keys that are used for search"""
    index = item['defindex']
    name = item['item_name']
    classes = getitemclasses(item)
    attributes = getitemattributes(item, attributes, effects)
    storeprice = getstoreprice(item, storeprices)
    marketprice = getmarketprice(item, marketprices)
    tags = getitemtags(item)
    blueprint = sorted(blueprints[index],reverse=True) # Sort by chance

    description = ''
    if 'bundle' in tags and storeprice:
        descriptions = bundles[index]['descriptions']
        text = []
        items = []

        for i in range(len(descriptions)):
            key = str(i)
            value = descriptions[key]['value']
            if 'color' in descriptions[key]:
                items.append(value)
            else:
                text.append(value)

        description = '{0}---{1}'.format('\n'.join(text),'\n'.join(items))

    elif 'item_description' in item:
        description = item['item_description']
        if 'bundle' in tags and name in itemsets:
            description += '---'+'\n'.join(itemsets[name]['items'])

    itemdict = {'index':index,
                'name':name,
                'image':item['image_url'],
                'image_large':item['image_url_large'],
                'description':description,
                'attributes':attributes,
                'classes':classes,
                'tags':tags,
                'storeprice':storeprice,
                'marketprice':marketprice,
                'blueprints':blueprint}

    if 'paint' in tags:
        paintvalue = str(int(item['attributes'][1]['value']))
        # Ignore Paint Tool
        if paintvalue != '1':
            itemdict['image'] = itemdict['image_large'] = '/images/paints/Paint_Can_{}.png'.format(paintvalue)

    return itemdict

def getitemsdict(schema, bundles, blueprints, storeprices, marketprices):
    """Returns an ordered dictionary with index as key and an itemdict as value"""
    itemsdict = OrderedDict()
    items = getitems(schema)
    itemsets = getitemsets(schema)
    attributes = getattributes(schema)
    effects = getparticleeffects(schema)
    for idx in items:
        itemdict = createitemdict(items[idx],attributes,effects,itemsets,bundles,
                                  blueprints,storeprices,marketprices)
        itemsdict[idx] = itemdict

    return itemsdict

def parseinput(query):
    querylist = [i for i in splitspecial(query) if i not in ['the','a','of','s']]

    classes = []
    tags = []
    for word in querylist:
        class_ = getclass(word)
        tag = gettag(word)

        if class_:
            classes.append(class_)
        elif tag:
            tags.append(tag)

    if (len(tags) + len(classes)) != len(querylist):
        classes = tags = []

    return {'query':query,'querylist':querylist,'classes':classes,'tags':tags}

def getsetitems(itemset, itemsbyname, itemsdict):
    setitems = []
    for name in itemset['items']:
        name = name.replace('The ','').replace("Capone's Capper","Capo's Capper")
        setitems.append(itemsdict[itemsbyname[name]['defindex']])

    return setitems

def search(query, itemsdict, itemsbyname, itemsets):
    """This method parses the result obtained from parseinput and gets all the
    items that match this result. It returns a dict with two keys - mainitems,
    and otheritems. The mainitems value is a list for regular results while the
    otheritems value is a dict of lists for several different results"""
    mainitems = []
    otheritems = defaultdict(list)
    names = []

    result = parseinput(query)
    query = result['query']
    querylist = result['querylist']
    classes = result['classes']
    tags = result['tags']

    itemsetmatch = re.match('(.+) [sS]et',query)
    hasweapontag = not set(tags).isdisjoint(getweapontags())
    if classes or tags:
        for itemdict in itemsdict.values():
            itemclasses = itemdict['classes']
            itemtags = itemdict['tags']

            isclassmatch = not set(itemclasses).isdisjoint(classes) or not itemclasses
            if hasweapontag:
                istagmatch = set(tags).issubset(itemtags)
            else:
                istagmatch = not set(tags).isdisjoint(itemtags)

            if (isclassmatch or not classes) and (istagmatch or not tags):
                name = itemdict['name']
                index = itemdict['index']
                if itemdict['image'] and (index<496 or (512<index<680) or (698<index<8000)) and name not in names:
                    if len(itemclasses) == 1:
                        mainitems.append(itemdict)
                    elif len(itemclasses) > 1:
                        otheritems['Multi-Class Items'].append(itemdict)
                    else:
                        otheritems['All-Class Items'].append(itemdict)
                    names.append(name)

    elif query == 'all':
        mainitems = itemsdict.values()

    elif query == 'sets':
        for setname,itemset in itemsets.items():
            otheritems[setname].extend(getsetitems(itemset,itemsbyname,itemsdict))

    elif itemsetmatch:
        for setname,itemset in itemsets.items():
            if setname.lower() == itemsetmatch.group(1).lower():
                otheritems[setname].extend(getsetitems(itemset,itemsbyname,itemsdict))
                break

    else:
        for itemdict in itemsdict.values():
            itemname = splitspecial(itemdict['name'])

            match = not set(itemname).isdisjoint(querylist)

            if (match and itemdict['image'] and itemname not in names):
                mainitems.append(itemdict)
                names.append(itemname)

        for setname,itemset in itemsets.items():
            if not set(splitspecial(setname)).isdisjoint(querylist):
                otheritems[setname].extend(getsetitems(itemset,itemsbyname,itemsdict))

        mainitems = getsorteditemlist(mainitems,querylist)

    return {'mainitems':mainitems, 'otheritems':otheritems}

def getsorteditemlist(itemlist, querylist):
    """Return sorted itemlist based on the intersection between the
    search query words and each item's name"""
    return sorted(itemlist,key=lambda k: set(querylist).intersection(splitspecial(k['name'])),reverse=True)