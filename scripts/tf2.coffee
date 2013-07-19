root = exports ? this

class User
  constructor: ->
    @id = getCookie('steam_id')
    @loggedIn = Boolean(@id)
    @isOwnPage = (@loggedIn and @id == document.getElementById('steamid')
                                              ?.getAttribute('data-id'))

    @priceSource = getCookie('price_source') or 'backpack.tf'

class Item
  constructor: (elem) ->
    @name = elem.title
    @id = elem.getAttribute('data-index')
    @imageUrl = elem.getAttribute('data-image')
    @description = elem.getAttribute('data-description') or ''
    @attributes = elem.getElementsByTagName('div')?[0]?.innerHTML or ''
    @classes = elem.getAttribute('data-classes')
    @tags = (elem.getAttribute('data-tags') or '').split(',')
    @storePrice = elem.getAttribute('data-storeprice')
    @blueprints = elem.getElementsByTagName('ul')

    @wishIndex = elem.getAttribute('data-i')
    @qualityNo = elem.getAttribute('class')?.match(/quality-(\d+)/)?[1]

    @elem = elem

  marketPrice: (source) ->
    JSON.parse(@elem.getAttribute("data-#{ source }"))

class ItemBox
  constructor: (showLink=true) ->
    @showLink = showLink

    @user = new User()

    @itemBox = document.createElement('div')
    @itemBox.id = 'itembox'
    document.getElementsByTagName('body')[0].appendChild(@itemBox)

  show: (elem) ->
    @item = new Item(elem)

    @source = @user.priceSource
    @altSource = if @source is 'spreadsheet' then 'backpack.tf'
    else 'spreadsheet'

    @_generateItemBox()
    @itemBox.style.display = 'block'

  hide: ->
    @itemBox.style.display = 'none'

  _tagsHTML: ->
    if @item.tags.length
      tagsHTML = "<div id='tags'>"
      isWeapon = 'weapon' in @item.tags
      isToken = 'token' in @item.tags
      title = image = ''

      for i in ['primary','secondary','melee','pda2']
        if i in @item.tags
          if isWeapon
            title =  capitalize(i)+' Weapon'
            image = i

          else if isToken
            title = 'Slot Token'
            image = 'slot-token'

      for i in ['hat','misc','tool','bundle']
        if i in @item.tags
          title = capitalize(i)
          image = i

      if isToken and @item.classes
        title = 'Class Token'
        image = 'class-token'

      if title and image
        tagsHTML +=
          """
          <a href='/search?q=#{ encodeURIComponent(title) }'
           target='_blank' title='#{ title }' class='#{ image }'></a>
          """

      tagsHTML += "</div>"
    else tagsHTML = ''

  _nameHTML: ->
    nameHTML = @item.name

    if @showLink
      nameHTML =
        """
        <a href='/item/#{ @item.id }'
         target='_blank' class='glow' title='Go to Item Page'>
        #{ nameHTML }</a>
        """
    nameHTML = "<h2 id='itemname'>#{ nameHTML }</h2>"

  _classesHTML: ->
    if @item.classes
      classesHTML = "<div id='classes'>"
      for i in @item.classes.split(',')
        classesHTML +=
          """
          <a href='/search?q=#{ i }' target='_blank'
           class='#{ i.toLowerCase() }'></a>
         """
      classesHTML += '</div>'
    else classesHTML = ''

  _bundleHTML: ->
    # Link to bundle items HTML
    if 'bundle' in @item.tags and @item.description.indexOf('---') != -1
      bundleHTML =
        """
        <a href=\"/search?q=#{ encodeURIComponent(@item.name) }%20Set\"
         target='_blank'>
        <div class='rounded glow' style='display: inline-block; padding: 7px;'>
        View items
        </div>
        </a>
        """
    else bundleHTML = ''

  _priceSourceHTML: (source) ->
    priceHTML = ''

    for quality, price of @item.marketPrice(source)
      denomMatch = price.match(/(Refined|Key(s)?|Bud(s)?)/)

      if denomMatch
        denom = denomMatch[0]

        price = price.replace(/(\d+(\.\d+)?)/g,
          """
          <a href="/search?q=\$1%20#{ denom }"
           target="_blank" class="glow">\$1</a>
          """)
      priceHTML += "<span class='#{ quality.toLowerCase() }'>#{
        quality }</span>: #{ price }<br>"

    return priceHTML

  _pricesHTML: ->
    classifiedsURL = "http://backpack.tf/classifieds/search/#{
      encodeURIComponent(@item.name) }"

    priceSourceHTML = @_priceSourceHTML(@source)

    if not priceSourceHTML
      [@source, @altSource] = [@altSource, @source]
      priceSourceHTML = @_priceSourceHTML(@item, @source)

    if priceSourceHTML
      pricesHTML =
        """
        <div id="marketprice">
        <span id="pricesource">#{ capitalize(@source) }</span><br>
        <a href="#{ classifiedsURL }"
         id="classifieds" class="rounded-tight glow"
         target="_blank" style="color:rgb(129, 170, 197);display:none">
        Classifieds
        </a>
        <h3 id="prices">#{ priceSourceHTML }</h3></div>
        """
    else pricesHTML = ''

  _blueprintsHTML: ->
    if @item.blueprints.length
      blueprintsHTML = '<div id="blueprints">'
      for b in @item.blueprints
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
    else blueprintsHTML = ''

  _outpostHTML: ->
    """
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
    """

  _wishlistHTML: ->
    if @user.loggedIn
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
    else wishlistHTML = ''

  _buttonsHTML: ->
    wikiLink = "http://wiki.teamfortress.com/wiki/#{
      encodeURIComponent(@item.name) }"

    """
    <div id='buttons'>

    <a class='icon-info icon-large button-icon' target='_blank'
     title='Open in Wiki' href=\"#{ wikiLink }\"></a>

    <a class='icon-shopping-cart icon-large button-icon'
     target='_blank' title='Community Market'
     href=\"http://steamcommunity.com/market/search?q=appid%3A440
    %20#{ encodeURIComponent(@item.name) }\"></a>

    #{ @_outpostHTML() }
    #{ @_wishlistHTML() }
    </div>
    """

  _buyHTML: ->
    # Buy button and store price HTML
    if @item.storePrice
      buyHTML =
        """
        <div id='buy'>
        <form style='display:inline-block'>$#{ @item.storePrice }<br>
        <input type='text' value='1' size='1' id='quantity'
         class='textbox' style='text-align: right'>
        </form><a href='#' id='buybutton'></a></div>
        """
    else buyHTML = ''

  _pricesLink: ->
    priceButton = document.getElementById('pricesource')
    classifieds = document.getElementById('classifieds')

    # Show classifieds
    if classifieds and @source is 'backpack.tf'
      classifieds.style.display = 'inline'

    if priceButton and @item.marketPrice(@altSource)
      priceButton.style.cursor = 'pointer'

      priceButton.onclick = =>
        @altSource = if priceButton.innerHTML == 'Spreadsheet'
        then 'backpack.tf' else 'spreadsheet'

        priceButton.innerHTML = capitalize(@altSource)
        @prices.innerHTML = @_priceSourceHTML(@altSource)

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
        tradeType }\":\"440,#{ @item.id },#{ @form.quality.value }\"}"

      @form.submit.click()

  _wishlistLink: ->
    # Update wishlist item index
    if @user.isOwnPage
      for wish, idx in document.getElementsByClassName('item')
        if wish.getAttribute('data-i') == @item.wishIndex
          @item.wishIndex = idx.toString()
          break

    if @user.loggedIn
      wishlistAction = '/wishlist/add'
      wishlistButton = document.getElementById('wishlistbutton')

      if @user.isOwnPage
        wishlistAction = '/wishlist/remove'
        wishlistButton.setAttribute('title', 'Remove from wishlist')

      # Add to wishlist or remove from wishlist
      wishlistButton.onclick = =>
        wishlistData = {'index': @item.id, 'quality': @form.quality.value}

        if @user.isOwnPage
          wishlistData = {'i': @item.wishIndex}

        postAjax wishlistAction, wishlistData, (response) =>
          if response == 'Added'
            wishlistMessage = document.getElementById('wishlistmessage')
            wishlistMessage.style.display = 'block'
            wishlistMessage.setAttribute('class', 'animated fadeInLeft')
            setTimeout((->
              wishlistMessage.setAttribute('class', 'animated fadeOut')), 1000)
          else if response == 'Removed'
            @hide()
            @item.parentNode.removeChild(@item)

  _buyLink: ->
    buyButton = document.getElementById('buybutton')
    if buyButton
      buyButton.onclick = =>
        quantity = document.getElementById('quantity').value
        window.open("http://store.steampowered.com/buyitem/440/#{
          @item.id }/#{ quantity }")

  _generateItemBox: ->
    # Itembox HTML
    @itemBox.innerHTML =
      """
      #{ @_tagsHTML() }
      #{ @_nameHTML() }
      #{ @_classesHTML() }
      #{ @_bundleHTML() }
      #{ @_pricesHTML() }
      #{ @_blueprintsHTML() }
      #{ @_buttonsHTML() }
      #{ @_buyHTML() }
      """

    @form = document.tf2outpostform
    @prices = document.getElementById('prices')

    @_pricesLink()
    @_outpostLink()
    @_wishlistLink()
    @_buyLink()

    # Hover area
    hoverArea = document.createElement('div')
    hoverArea.title = @item.name
    hoverArea.setAttribute('data-description', @item.description)
    hoverArea.setAttribute('data-tags', @item.tags)
    hoverArea.id = 'hoverarea'
    hoverArea.style.backgroundImage = "url('#{ @item.imageUrl }')"

    # Add hover area to itembox
    ref = document.getElementById('blueprints') or
      document.getElementById('buttons')
    @itemBox.insertBefore(hoverArea, ref)

    # Enable hover box
    new HoverBox(hoverArea)

    # Auto quality selection
    if @item.name.indexOf('Strange') == -1
      # Wishlist item quality
      if @item.qualityNo
        @form.quality.value = @item.qualityNo
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
      document.getElementsByTagName('body')[0].appendChild(@hoverBox)

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

    item = new Item(e.target)
    description = escapeHTML(item.description)

    if description
      if 'bundle' in item.tags and description.indexOf('---') != -1
        descList = description.split('---')
        description = """
                      #{ descList[0] }
                      <span style='color:#95af0c'>#{ descList[1] }</span>
                      """
      description = "<br>#{ description }"

    @hoverBox.innerHTML =
      """
      <div style='font-size:1.2em;color:rgb(230,230,230)'>#{ title }</div>#{
      item.attributes }#{ description }
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

capitalize = (word) ->
  word[0].toUpperCase() + word[1...]

escapeHTML = (string) ->
  string.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

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
