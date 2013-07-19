root = exports ? this

capitalize = (word) ->
  word[0].toUpperCase() + word[1...]

escapeHTML = (string) ->
  string.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

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
        """
        <a href=\"/search?q=\$1%20#{ denom }\"
         target='_blank' class='glow'>\$1</a>
        """)

    marketPrice = priceList.join(', ')
                           .replace(/[{}']/g,'')
                           .replace(/, /g,'<br>')

    for i in ['Unique','Vintage','Strange','Genuine','Haunted','Unusual']
      re = new RegExp(i,"g")
      marketPrice = marketPrice
                .replace(re,"<span class='#{ i.toLowerCase() }'>#{ i }</span>")

  return marketPrice

class ItemBox
  constructor: (showLink=true) ->
    @showLink = showLink
    @loggedInId = getCookie('steam_id')
    @isOwnPage = (@loggedInId and
                  @loggedInId == document.getElementById('steamid')
                                        ?.getAttribute('data-id'))

    @itemBox = document.createElement('div')
    @itemBox.id = 'itembox'
    document.getElementById('container').appendChild(@itemBox)

  show: (item) ->
    @id = item.getAttribute('data-index')
    @name = item.title
    @description = getDescription(item)
    @storePrice = item.getAttribute('data-storeprice')
    @imageUrl = item.getAttribute('data-image')
    @blueprints = item.getElementsByTagName('ul')
    @classes = item.getAttribute('data-classes')
    @tags = getTags(item)

    @item = item

    @cookiePrice = getCookie('price_source')
    @source = @cookiePrice or 'backpack.tf'

    @altSource = if @source is 'spreadsheet' then 'backpack.tf'
    else 'spreadsheet'

    @_generateItemBox()
    @itemBox.style.display = 'block'

  hide: ->
    @itemBox.style.display = 'none'

  _tagsHTML: ->
    tagsHTML = "<div id='tags' style='position:absolute;top:-5px;left:5px'>"
    if @tags.length
      isWeapon = 'weapon' in @tags
      isToken = 'token' in @tags
      title = image = ''

      for i in ['primary','secondary','melee','pda2']
        if i in @tags
          if isWeapon
            title =  capitalize(i)+' Weapon'
            image = i

          else if isToken
            title = 'Slot Token'
            image = 'slot-token'

      for i in ['hat','misc','tool','bundle']
        if i in @tags
          title = capitalize(i)
          image = i

      if isToken and @classes
        title = 'Class Token'
        image = 'class-token'

      if title and image
        tagsHTML +=
          """
          <a href='/search?q=#{ encodeURIComponent(title) }'
           target='_blank' title='#{ title }' class='#{ image }'></a>
          """

      tagsHTML += "</div>"

    return tagsHTML

  _nameHTML: ->
    nameHTML = @name

    if @showLink
      nameHTML =
        """
        <a href='/item/#{ @id }'
         target='_blank' class='glow' title='Go to Item Page'>
        #{ nameHTML }</a>
        """
    nameHTML = "<h2 id='itemname'>#{ nameHTML }</h2>"

    return nameHTML

  _classesHTML: ->
    classesHTML = "<div id='classes' style='position:absolute;top:0;right:0'>"
    if @classes
      for i in @classes.split(',')
        classesHTML +=
          """
          <a href='/search?q=#{ i }' target='_blank'
           class='#{ i.toLowerCase() }'></a>
         """
    classesHTML += '</div>'

    return classesHTML

  _bundleHTML: ->
    # Link to bundle items HTML
    if 'bundle' in @tags and @description.indexOf('---') != -1
      bundleHTML =
        """
        <a href=\"/search?q=#{ encodeURIComponent(@name) }%20Set\"
         target='_blank'>
        <div class='rounded glow' style='display: inline-block; padding: 7px;'>
        View items
        </div>
        </a>
        """
    else
      bundleHTML = ''

    return bundleHTML

  _pricesHTML: ->
    pricesHTML = getMarketPrice(@item, @source)
    if not pricesHTML
      [@source, @altSource] = [@altSource, @source]
      pricesHTML = getMarketPrice(@item, @source)

    classifiedsURL = "http://backpack.tf/classifieds/search/#{
      encodeURIComponent(@name) }"

    if pricesHTML
      pricesHTML =
        """
        <div id='marketprice'>
        <span id='pricesource'>#{ capitalize(@source) }</span><br>
        <a href='#{ classifiedsURL }'
         id='classifieds' class='rounded-tight glow'
         target='_blank' style='color:rgb(129, 170, 197);display:none'>
        Classifieds
        </a>
        <h3 id='prices'>#{ pricesHTML }</h3>
        </div>
        """

    return pricesHTML

  _blueprintsHTML: ->
    blueprintsHTML = ''
    if @blueprints.length
      blueprintsHTML = '<div id="blueprints">'
      for b in @blueprints
        chance = b.getAttribute('data-chance')

        blueprintsHTML += '<div class="blueprint">'
        for i in b.getElementsByTagName('li')
          for j in [0...i.getAttribute('data-count')]
            name = i.title
            index = i.getAttribute('data-index')
            style = "background-image:url(#{ i.getAttribute('data-image') });"
            listItem =  "<div title=\"#{ name }\" class='item-small' style='#{
              style }'></div>"
            if index
              url = "/item/#{ index }"
            else
              name = name.replace('Any ','').replace('Spy Watch','PDA2 Weapon')
              if name.split(' ').length > 2
                name = name.replace('Weapon','Set')
              url = "/search?q=#{ encodeURIComponent(name) }"

            listItem = "<a href=\"#{ url }\" target='_blank'>#{ listItem }</a>"
            blueprintsHTML += listItem

        blueprintsHTML +=
          """
          <div title='Crafting Chance' style='position:absolute;right:10px;'>
          <h3>#{ chance }%</h3></div></div>
          """

      blueprintsHTML += '</div>'

    return blueprintsHTML

  _wishlistHTML: ->
    if @loggedInId
      wishlistHTML =
        """
        <div style='display: inline-block; width: 40px'>
        <div id='wishlistmessage'
         style='display: none;margin:0 0 4px -18px'>Added</div>
        <i id='wishlistbutton' class='button-icon rounded icon-star icon-large'
         style='background-color: transparent'
         title='Add to wishlist'></i>
        </div>
        """
    else
      wishlistHTML = ''

    return wishlistHTML

  _buyHTML: ->
    # Buy button and store price HTML
    if @storePrice
      buyHTML =
        """
        <div id='buy'>
        <form style='display:inline-block'>$#{ @storePrice }<br>
        <input type='text' value='1' size='1' id='quantity'
         class='textbox' style='text-align: right'>
        </form><a href='#' id='buybutton'></a></div>
        """
    else
      buyHTML = ''

    return buyHTML

  _marketPriceLink: ->
    priceButton = document.getElementById('pricesource')
    classifieds = document.getElementById('classifieds')

    # Show classifieds
    if classifieds and @source is 'backpack.tf'
      classifieds.style.display = 'inline'

    if priceButton and @item.getAttribute("data-#{ @altSource }")
      priceButton.style.cursor = 'pointer'

      priceButton.onclick = =>
        @altSource = if priceButton.innerHTML == 'Spreadsheet'
        then 'backpack.tf' else 'spreadsheet'

        priceButton.innerHTML = capitalize(@altSource)
        @prices.innerHTML = getMarketPrice(@item, @altSource)

        if @altSource is 'backpack.tf'
          classifieds.style.display = 'inline'
        else
          classifieds.style.display = 'none'

      priceButton.onmouseover = ->
        priceButton.style.textShadow = '0 0 10px rgb(196, 241, 128)'

      priceButton.onmouseout = ->
        priceButton.style.textShadow = ''

  _outpostLink: ->
    # TF2Outpost link
    if window.navigator.userAgent.indexOf('Valve Steam GameOverlay') == -1
      @form.setAttribute('target', '_blank')

    document.getElementById('find-trades-btn').onclick = (event) =>
      tradeType = document.getElementById('tradetype').value

      @form.json.value = "{\"filters\":{},\"#{
        tradeType }\":\"440,#{ @id },#{ @form.quality.value }\"}"

      @form.submit.click()

  _wishlistLink: ->
    if @isOwnPage
      wishIndex = @item.getAttribute('data-i')
      for wish, idx in document.getElementsByClassName('item')
        if wish.getAttribute('data-i') == wishIndex
          wishIndex = idx.toString()
          break

    if @_wishlistHTML()
      wishlistAction = '/wishlist/add'
      wishlistButton = document.getElementById('wishlistbutton')

      if @isOwnPage
        wishlistAction = '/wishlist/remove'
        wishlistButton.setAttribute('title', 'Remove from wishlist')

      # Add to wishlist or remove from wishlist
      wishlistButton.onclick = =>
        wishlistData = {'index': @id, 'quality': @form.quality.value}

        if @isOwnPage
          wishlistData = {'i': wishIndex}

        postAjax wishlistAction, wishlistData, (response) =>
          if response == 'Added'
            wishlistMessage = document.getElementById('wishlistmessage')
            wishlistMessage.style.display = 'block'
            wishlistMessage.setAttribute('class', 'animated fadeInLeft')
            setTimeout((->
              wishlistMessage.setAttribute('class', 'animated fadeOut')),
                1000)
          else if response == 'Removed'
            @hide()
            @item.parentNode.removeChild(@item)

  _buyLink: ->
    buyButton = document.getElementById('buybutton')
    if buyButton
      buyButton.onclick = =>
        quantity = document.getElementById('quantity').value
        window.open("http://store.steampowered.com/buyitem/440/#{
          @id }/#{ quantity }")

  _generateItemBox: ->
    wikiLink = "http://wiki.teamfortress.com/wiki/#{
      encodeURIComponent(@name) }"

    # Itembox HTML
    @itemBox.innerHTML =
      """
      #{ @_tagsHTML() }
      #{ @_nameHTML() }
      #{ @_classesHTML() }
      #{ @_bundleHTML() }
      #{ @_pricesHTML() }
      #{ @_blueprintsHTML() }
      <div id='buttons'>

      <a class='icon-info icon-large button-icon' target='_blank'
       title='Open in Wiki' href=\"#{ wikiLink }\"></a>

      <a class='icon-shopping-cart icon-large button-icon'
       target='_blank' title='Community Market'
       href=\"http://steamcommunity.com/market/search?q=appid%3A440
      %20#{ encodeURIComponent(@name) }\"></a>

      <a href='#' id='find-trades-btn'
       class='icon-exchange icon-large button-icon' title='Find Trades'></a>

      <form name='tf2outpostform' method='POST' style='display:inline-block'
       action='http://www.tf2outpost.com/search'>

      <input type='hidden' name='json'>
      <input type='hidden' name='type' value='any'>
      <input type='submit' name='submit' value='Search' style='display:none'>

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

      #{ @_wishlistHTML() }
      </div>
      #{ @_buyHTML() }
      """

    @form = document.tf2outpostform
    @prices = document.getElementById('prices')

    @_marketPriceLink()
    @_outpostLink()
    @_wishlistLink()
    @_buyLink()

    # Hover area
    hoverArea = document.createElement('div')
    hoverArea.title = @name
    hoverArea.setAttribute('data-description', @description)
    hoverArea.setAttribute('data-tags', @tags)
    hoverArea.id = 'hoverarea'
    hoverArea.style.backgroundImage = "url('#{ @imageUrl }')"
    @hoverBox = new HoverBox(hoverArea)

    # Add hover area to itembox
    ref = document.getElementById('blueprints') or
      document.getElementById('buttons')
    @itemBox.insertBefore(hoverArea, ref)

    # Auto quality selection
    if @name.indexOf('Strange') == -1
      # Wishlist item quality
      qualityNo = @item.getAttribute('class').match(/quality-(\d+)/)
      if qualityNo
        @form.quality.value = qualityNo[1]
      else if @prices
        for option, i in @form.quality.options
          if @prices.innerHTML.indexOf(option.innerHTML) != -1
            @form.quality.selectedIndex = i
            break

class HoverBox
  constructor: (itemBoxOrElem) ->
    @itemBox = if itemBoxOrElem instanceof ItemBox then itemBoxOrElem else null
    if not @itemBox
      elem = itemBoxOrElem

    @hoverBox = document.getElementById('hoverbox')

    if not @hoverBox
      @hoverBox = document.createElement('div')
      @hoverBox.id = 'hoverbox'
      document.getElementById('container').appendChild(@hoverBox)

    @_add(elem)

  _add: (elem) ->
    list = if elem then [elem] else document.getElementsByClassName('item')

    for item in list
      item.addEventListener("mouseout", @_hide, false)
      item.addEventListener("mousemove", @_moveMouse, false)
      item.addEventListener("mouseover", @_show, false)
      if not elem
        item.addEventListener("click", @_clickItem, false)

    if not elem
      document.getElementById('container').addEventListener("click",
                                                            @_hideItemBox,
                                                            false)
      document.onkeydown = (e) =>
        if e.keyCode == 27
          @itemBox.hide()

  _show: (e) =>
    title = e.target.title

    attributes = getAttributes(e.target)
    description = escapeHTML(getDescription(e.target))

    if description
      if 'bundle' in getTags(e.target) and description.indexOf('---') != -1
        descList = description.split('---')
        description = """
                      #{ descList[0] }<br>
                      <span style='color:#95af0c'>#{ descList[1] }</span>
                      """
      description = "<br>#{ description }"

    @hoverBox.innerHTML =
      """
      <div style='font-size:1.2em;color:rgb(230,230,230)'>#{ title }</div>#{
      attributes }#{ description }
      """

    @hoverBox.style.display = 'block'

  _hide: =>
    @hoverBox.style.display = 'none'

  _hideItemBox: (e) =>
    a = e.target
    if a.getAttribute('class') != 'item'
      els = []
      while a
        els.push(a)
        a = a.parentNode

      if @itemBox.itemBox not in els
        @itemBox.hide()

  _moveMouse: (e) =>
    @hoverBox.style.top = "#{ e.pageY + 28 }px"
    @hoverBox.style.left = "#{ e.pageX - 154 }px"

  _clickItem: (e) =>
    @itemBox.show(e.target)
    e.preventDefault()
    e.stopPropagation()

setCookie = (name, value, days) ->
  expires = ''

  if days
    date = new Date()
    date.setDate(date.getDate() + days)
    expires = ";expires=#{ date.toUTCString() }"

   document.cookie = "#{ name }=#{ value }#{ expires }"

getCookie = (name) ->
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

root.ItemBox = ItemBox
root.HoverBox = HoverBox

root.getCookie = getCookie
root.setCookie = setCookie
