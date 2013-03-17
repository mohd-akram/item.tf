escapeHTML = (string) ->
  string.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

capitalize = (word) ->
  word[0].toUpperCase() + word[1...]

getAttributes = (item) ->
  divs = item.getElementsByTagName('div')
  if divs.length then divs[0].innerHTML else ''

getDescription = (item) ->
  item.getAttribute('data-description') or ''

getTags = (item) ->
  (item.getAttribute('data-tags') or '').split(',')

getMarketPrice = (item, source) ->
  marketPrice = item.getAttribute("data-#{ source }") or ''
  if marketPrice
    priceList = []
    for i in marketPrice.split(', ')
      denomMatch = i.match(/(Refined|Key(s)?|Bud(s)?)/g)

      if not denomMatch
        priceList.push i
        continue

      denom = denomMatch[0]

      priceList.push i.replace(/(\d+(\.\d+)?)/g,
      "<a href=\"/search?q=\$1%20#{ denom }\"
 target='_blank' class='glow'>\$1</a>")

    marketPrice = priceList.join(', ')
                           .replace(/[{}']/g,'')
                           .replace(/, /g,'<br>')

    for i in ['Unique','Vintage','Strange','Genuine','Haunted','Unusual']
      re = new RegExp(i,"g")
      marketPrice = marketPrice
                .replace(re,"<span class='#{ i.toLowerCase() }'>#{ i }</span>")

  return marketPrice

show = (e) ->
  title = e.target.title

  attributes = getAttributes(e.target)
  description = escapeHTML(getDescription(e.target))

  if description
    if 'bundle' in getTags(e.target) and description.indexOf('---') != -1
      descList = description.split('---')
      description = "#{ descList[0] }<br>
<span style='color:#95af0c'>#{ descList[1] }</span>"
    description = "<br>#{ description }"

  hoverBox.innerHTML = "<div style='font-size:1.2em;color:rgb(230,230,230)'>
#{ title }</div>#{ attributes }#{ description }"

  hoverBox.style.display = "block"

hide = ->
  hoverBox.style.display = "none"

moveMouse = (e) ->
  hoverBox.style.top = "#{ e.pageY + 28 }px"
  hoverBox.style.left = "#{ e.pageX - 154 }px"

clickItem = (e) ->
  showItemInfo(e.target)
  e.preventDefault()
  e.stopPropagation()

hideItemBox = (e) ->
  a = e.target
  if a.getAttribute('class') != 'item'
    els = []
    while a
      els.push(a)
      a = a.parentNode

    if itemBox not in els
      itemBox.style.display = 'none'

init = ->
  window.hoverBox = document.getElementById("hoverbox")
  window.itemBox = document.getElementById("itembox")

window.showItemInfo = (item, link=true) ->
  init()

  loggedInId = getCookie('steam_id')
  cookiePrice = getCookie('price_source')

  source = cookiePrice or 'backpack.tf'

  altSource = if source == 'spreadsheet' then 'backpack.tf' else 'spreadsheet'

  isOwnPage = (loggedInId and loggedInId == document.getElementById('steamid')
                                                   ?.getAttribute('data-id'))
  if isOwnPage
    wishIndex = item.getAttribute('data-i')
    for wish, idx in document.getElementsByClassName('item')
      if wish.getAttribute('data-i') == wishIndex
        wishIndex = idx.toString()
        break

  # Market price HTML
  marketPrice = getMarketPrice(item, source)
  if not marketPrice
    [source, altSource] = [altSource, source]
    marketPrice = getMarketPrice(item, source)

  if marketPrice
    marketPrice = "<span id='pricesource'>#{ capitalize(source) }</span><br>
<h3 id='prices'>#{ marketPrice }</h3>"

  itemId = item.getAttribute('data-index')
  description = getDescription(item)
  storePrice = item.getAttribute('data-storeprice')
  imageUrl = item.getAttribute('data-image')
  blueprints = item.getElementsByTagName('ul')

  # Blueprints HTML
  blueprintsHTML = ''
  if blueprints.length
    blueprintsHTML = '<div id="blueprints">'
    for b in blueprints
      chance = b.getAttribute('data-chance')

      blueprintsHTML += '<div class="blueprint">'
      for i in b.getElementsByTagName('li')
        for j in [0...i.getAttribute('data-count')]
          name = i.title
          index = i.getAttribute('data-index')
          style = "background-image:url(#{ i.getAttribute('data-image') });"
          listItem =  "<div title=\"#{ name }\" class='item-small'
 style='#{ style }'></div>"
          if index
            url = "/item/#{ index }"
          else
            name = name.replace('Any ','').replace('Spy Watch','PDA2 Weapon')
            if name.split(' ').length > 2
              name = name.replace('Weapon','Set')
            url = "/search?q=#{ encodeURIComponent(name) }"

          listItem = "<a href=\"#{ url }\" target='_blank'>#{ listItem }</a>"
          blueprintsHTML += listItem

      blueprintsHTML += "<div title='Crafting Chance'
 style='position:absolute;right:10px;'>
<h3>#{ chance }%</h3></div></div>"

    blueprintsHTML += '</div>'

  # Wishlist HTML
  wishlistHTML = if loggedInId then "
<div style='display: inline-block; width: 40px'>
<div id='wishlistmessage'
 style='display: none;margin:0 0 4px -18px'>Added</div>
<i id='wishlistbutton' class='button-icon rounded icon-star icon-large'
 style='background-color: transparent'
 title='Add to wishlist'></i>
</div>" else ''

  # Buy button and price HTML
  buyHTML = if storePrice then "<div id='buy'><form
 style='display:inline-block'>$#{ storePrice }<br>
<input type='text' value='1' size='1' id='quantity'
 class='textbox' style='text-align: right'>
</form><a href='#' id='buybutton'></a></div>" else ''

  # Classes HTML
  classesHTML = "<div id='classes' style='position:absolute;top:0;right:0'>"
  classes = item.getAttribute('data-classes')
  if classes
    for i in classes.split(',')
      classesHTML += "<a href='/search?q=#{ i }' target='_blank'>
<img title='#{ i }' alt='#{ i }' width='40' height='40'
 src='/images/items/#{ i }_icon.png'></a><br>"
  classesHTML += "</div>"

  # Tags HTML
  tagsHTML = "<div id='tags' style='position:absolute;top:-5px;left:5px'>"
  tags = getTags(item)
  if tags.length
    isWeapon = 'weapon' in tags
    isToken = 'token' in tags
    title = image = ''

    for i in ['primary','secondary','melee','pda2']
      if i in tags
        if isWeapon
          title =  capitalize(i)+' Weapon'
          image = i

        else if isToken
          title = 'Slot Token'
          image = 'slot_token'

    for i in ['hat','misc','tool','bundle']
      if i in tags
        title = capitalize(i)
        image = i

    if isToken and classes
      title = 'Class Token'
      image = 'class_token'

    if title and image
      tagsHTML += "<a href='/search?q=#{ encodeURIComponent(title) }'
 target='_blank'>
<img title='#{ title }' alt='#{ title }' width='50' height='50'
 src='/images/items/#{ image }.png'></a><br>"
  tagsHTML += "</div>"

  # Link to bundle items HTML
  bundleHTML = if 'bundle' in tags and description.indexOf('---') != -1  then "
<a href=\"/search?q=#{ encodeURIComponent(item.title) }%20Set\"
 target='_blank'>
<div class='rounded glow' style='display: inline-block; padding: 7px;'>
View items</div></a>" else ''
  
  itemName = item.title
  if link
    itemName = "<a href='/item/#{ itemId }'
 target='_blank' class='glow' title='Go to Item Page'>
#{ itemName }</a>"

  wikiLink = "http://wiki.teamfortress.com/wiki/
#{ encodeURIComponent(item.title) }"

  # Itembox HTML
  itemBox.innerHTML = "
#{ tagsHTML }
<h2 id='itemname'>#{ itemName }</h2>
#{ classesHTML }
#{ bundleHTML }
<div id='marketprice'>#{ marketPrice }</div>
#{ blueprintsHTML }
<div id='buttons'>
<a class='button-small' target='_blank' title='Open in Wiki'
 href=\"#{ wikiLink }\">Wiki</a>
<a class='button-small' target='_blank' title='Community Market'
 href=\"http://steamcommunity.com/market/search?q=appid%3A440
%20#{ encodeURIComponent(item.title) }\">Market</a>

<form name='tf2outpostform' method='POST' style='display:inline-block'
 action='http://www.tf2outpost.com/search'>

<input type='hidden' name='json'>

<input class='button-small' type='submit'
 title='Find Trades' name='submit' value='Trades'>

<input type='hidden' name='type' value='any'>

<select id='tradetype' class='textbox'>
  <option value='has1'>Want</option>
  <option value='wants1'>Have</option>
</select>

<select id='quality' class='textbox'>
  <option value='6'>Unique</option>
  <option value='3'>Vintage</option>
  <option value='11'>Strange</option>
  <option value='1'>Genuine</option>
  <option value='13'>Haunted</option>
  <option value='5'>Unusual</option>
</select>

</form>

#{ wishlistHTML }
</div>
#{ buyHTML }
"

  # Hover area
  hoverArea = document.createElement('div')
  hoverArea.title = item.title
  hoverArea.setAttribute('data-description', description)
  hoverArea.setAttribute('data-tags', tags)
  hoverArea.id = 'hoverarea'
  hoverArea.style.backgroundImage = "url('#{ imageUrl }')"
  hoverArea.innerHTML = "<div style='display:none'>
#{ getAttributes(item) }</div>"
  hoverArea.addEventListener("mouseout", hide, false)
  hoverArea.addEventListener("mousemove", moveMouse, false)
  hoverArea.addEventListener("mouseover", show, false)
  itemBox.insertBefore(hoverArea, document.getElementById('blueprints'))

  # Buy button link
  buyButton = document.getElementById('buybutton')
  if buyButton
    buyButton.onclick = ->
      quantity = document.getElementById('quantity').value
      window.open("http://store.steampowered.com/buyitem/440/
#{ itemId }/#{ quantity }")

  # TF2Outpost link
  form = document.tf2outpostform

  if window.navigator.userAgent.indexOf('Valve Steam GameOverlay') == -1
    form.setAttribute('target', '_blank')

  quality = form.quality

  form.onsubmit = ->
    tradeType = document.getElementById('tradetype').value

    form.json.value = "{\"filters\":{},
\"#{ tradeType }\":\"440,#{ itemId },#{ quality.value }\"}"

  # Wishlist link
  if wishlistHTML
    wishlistAction = '/wishlist/add'
    wishlistButton = document.getElementById('wishlistbutton')

    if isOwnPage
      wishlistAction = '/wishlist/remove'
      wishlistButton.setAttribute('title', 'Remove from wishlist')
      
    # Add to wishlist or remove from wishlist
    wishlistButton.onclick = ->
      wishlistData = {'index': itemId, 'quality': quality.value}

      if isOwnPage
        wishlistData = {'i': wishIndex}

      postAjax wishlistAction, wishlistData, (response) ->
        if response == 'Added'
          wishlistMessage = document.getElementById('wishlistmessage')
          wishlistMessage.style.display = 'block'
          wishlistMessage.setAttribute('class', 'animated fadeInLeft')
          setTimeout((->
            wishlistMessage.setAttribute('class', 'animated fadeOut')),
              1000)
        else if response == 'Removed'
          itemBox.style.display = 'none'
          item.parentNode.removeChild(item)

  # Market price link
  priceButton = document.getElementById('pricesource')
  prices = document.getElementById('prices')

  if priceButton and item.getAttribute("data-#{ altSource }")
    priceButton.style.cursor = 'pointer'

    priceButton.onclick = ->
      altSource = if priceButton.innerHTML == 'Spreadsheet'
      then 'backpack.tf' else 'spreadsheet'

      priceButton.innerHTML = capitalize(altSource)
      prices.innerHTML = getMarketPrice(item, altSource)

    priceButton.onmouseover = ->
      priceButton.style.textShadow = '0 0 10px rgb(196, 241, 128)'

    priceButton.onmouseout = ->
      priceButton.style.textShadow = ''

  if itemName.indexOf('Strange Part') == -1
    # Auto quality selection
    qualityNo = item.getAttribute('class').match(/quality-(\d+)/)
    if qualityNo
      quality.value = qualityNo[1]
    else
      for option, i in quality.options
        if marketPrice.indexOf(option.innerHTML) != -1
          quality.selectedIndex = i
          break

  # Show the item info box
  itemBox.style.display = "block"

window.addHoverBox = ->
  init()
  for item in document.getElementsByClassName('item')
    item.addEventListener("mouseout", hide, false)
    item.addEventListener("mousemove", moveMouse, false)
    item.addEventListener("mouseover", show, false)
    item.addEventListener("click", clickItem, false)

  document.getElementById('container').addEventListener("click",
                                                        hideItemBox,
                                                        false)
  document.onkeydown = (e) ->
    if e.keyCode == 27
      itemBox.style.display = 'none'

window.setCookie = (name, value, days) ->
  expires = ''

  if days
    date = new Date()
    date.setDate(date.getDate() + days)
    expires = ";expires=#{ date.toUTCString() }"

   document.cookie = "#{ name }=#{ value }#{ expires }"

window.getCookie = (name) ->
  cookies = document.cookie.split(';')
  
  for cookie in cookies
    while cookie[0] == ' '
      cookie = cookie[1...]

    if cookie[...name.length] == name
      return cookie[name.length + 1...]

ajax = (url, callback) ->
  ajaxRequest = getAjaxRequest(callback)
  ajaxRequest.open("GET", url, true)
  ajaxRequest.setRequestHeader('X-Requested-With', 'XMLHttpRequest')
  ajaxRequest.send(null)

postAjax = (url, data, callback) ->
  ajaxRequest = getAjaxRequest(callback)
  ajaxRequest.open("POST", url, true)
  ajaxRequest.setRequestHeader("Content-Type",
                               "application/x-www-form-urlencoded")

  dataList = []
  for name, value of data
    dataList.push  "#{ name }=#{ value }"

  ajaxRequest.send(dataList.join('&'))

getAjaxRequest = (callback) ->
  try
    ajaxRequest = new XMLHttpRequest()
  catch e
    try
      ajaxRequest = new ActiveXObject("Msxml2.XMLHTTP")
    catch e
      try
        ajaxRequest = new ActiveXObject("Microsoft.XMLHTTP")
      catch e
        return null

  ajaxRequest.onreadystatechange = ->
    if ajaxRequest.readyState == 4
      callback(ajaxRequest.responseText)

  return ajaxRequest
