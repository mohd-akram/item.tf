root = exports ? this

priceSources = ['backpack.tf']

class User
  constructor: ->
    @id = getCookie 'steam_id'
    @loggedIn = Boolean(@id)

    Object.defineProperties @,
      priceSource:
        get: -> getCookie('price_source') or priceSources[0]
        set: (source) -> setCookie 'price_source', source, 365

  isOwnPage: -> @loggedIn and @id is
    document.getElementById('steamid')?.getAttribute('data-id')

class Item
  constructor: (@elem) ->
    @name = @elem.title
    @id = @elem.getAttribute 'data-index'
    @url = @elem.getAttribute 'data-url'
    @imageURL = @elem.getAttribute 'data-image'
    @description = @elem.getAttribute('data-description') or ''
    @level = @elem.getAttribute 'data-level'
    @attributes = @elem.getElementsByClassName('attrs')[0]?.innerHTML or ''
    @classes = @elem.getAttribute('data-classes')?.split(',') or []
    @tags = @elem.getAttribute('data-tags')?.split(',') or []
    @storePrice = @elem.getAttribute 'data-storeprice'
    @blueprints = @elem.getElementsByClassName('prints')[0]
      ?.getElementsByTagName('div') or []

    @prices = {}
    for source in priceSources
      price = JSON.parse(@elem.getAttribute("data-#{source}")
                             ?.replace('Collector"s', "Collector's") ? null)
      @prices[source] = price if price

    @wishIndex = @elem.getAttribute 'data-i'
    @qualityNo = @elem.className.match(/quality-(\d+)/)?[1]

class ItemBox
  constructor: (@showLink=true) ->
    @elem = document.createElement 'div'
    @elem.id = 'itembox'
    document.body.appendChild @elem

  show: (@item) ->
    @sources = (source for source in priceSources when source of @item.prices)
    @source = user.priceSource

    @_generate()
    @elem.style.display = 'block'

  hide: -> @elem.style.display = 'none'

  _nextPriceSource: ->
    @source = @sources[(@sources.indexOf(@source) + 1) % @sources.length]

  _tagsHTML: ->
    if @item.tags.length
      html = '<div id="tags">'
      isWeapon = 'weapon' in @item.tags
      isToken = 'token' in @item.tags

      for i in ['primary', 'secondary', 'melee', 'pda2']
        if i in @item.tags
          if isWeapon
            [title, image] = ["#{capitalize i} Weapon", i]

          else if isToken
            [title, image] = ['Slot Token', 'slot-token']

      for i in ['hat', 'misc', 'tool', 'bundle']
        if i in @item.tags
          [title, image] = [capitalize(i), i]

      if isToken and @item.classes.length
        [title, image] = ['Class Token', 'class-token']

      if title? and image?
        html +=
          """
          <a href="/search?q=#{encodeURIComponent title}"
           target="_blank" title="#{title}" class="#{image}"><img
           src="/images/tags.png" alt="#{title}"></a>
          """

      html += '</div>'
    else ''

  _nameHTML: ->
    html = @item.name

    if @showLink
      html =
        """
        <a href="#{@item.url}"
         class="glow" title="Go to Item Page">#{html}</a>
        """
    html =
      """
      <h2 id="itemname">#{html}</h2>
      <i id="shortlinkbutton" class="fa fa-caret-square-down"
       title="Short URL"></i><br>
      <div id="shortlink" style="display:none">
      <input type="text" value="https://item.tf/#{@item.id}" title="Shortlink"
       readonly><br>
      </div>
      """

  _classesHTML: ->
    if @item.classes.length
      html = '<div id="classes">'
      for class_ in @item.classes
        html +=
          """
          <a href="/search?q=#{class_}" target="_blank"
           title="#{class_}" class="#{class_.toLowerCase()}"><img
           src="/images/classes.png" alt="#{class_}"></a>
          """
      html += '</div>'
    else ''

  _bundleHTML: ->
    # Link to bundle items HTML
    if 'bundle' in @item.tags and @item.description.indexOf('---') isnt -1
      """
      <a href="/search?q=#{encodeURIComponent @item.name}%20Set"
       target="_blank">
      <div class="rounded glow" style="display: inline-block; padding: 7px">
      View Items
      </div>
      </a>
      """
    else ''

  _priceSourceHTML: ->
    html = ''

    unless @item.prices[@source]
      @_nextPriceSource()

    if @item.prices[@source]
      qualities = Object.keys(@item.prices[@source]).sort()
      for quality in qualities
        price = @item.prices[@source][quality]
        denomMatch = price.match(/(Refined|Key(s)?|Bud(s)?)/)

        if denomMatch
          denom = denomMatch[0]

          price = price.replace /(\d+(\.\d+)?)/g,
            "<a href='/search?q=\$1%20#{denom}'
              target='_blank' class='glow'>\$1</a>"

        html +=
          """
          <a href="/search?q=#{quality}" target="_blank"
           class="#{quality.toLowerCase().replace "'", ''}">#{
           quality}</a>: #{price}<br>
          """

    return html

  _pricesHTML: ->
    html = @_priceSourceHTML()
    if html then "<div id='marketprice'><span id='pricesource'>#{
      capitalize @source}</span><div id='prices'>#{html}</div></div>" else ''

  _blueprintsHTML: ->
    if @item.blueprints.length
      html = '<ul id="blueprints">'
      for blueprint in @item.blueprints
        chance = blueprint.getAttribute 'data-chance'

        html += '<li class="blueprint"><ul>'
        for item in blueprint.getElementsByTagName 'span'
          for i in [0...item.getAttribute 'data-count']
            name = item.title
            index = item.getAttribute 'data-index'

            listItem = "<img src=\"#{item.getAttribute 'data-image'}\" alt=\"#{
              name}\">"

            url = item.getAttribute 'data-url'

            unless url
              name = name
                .replace 'Any ', ''
                .replace 'Spy Watch', 'PDA2 Weapon'

              if name.split(' ').length > 2
                name = name.replace 'Weapon', 'Set'

              url = "/search?q=#{encodeURIComponent name}"

            html += "<li><a title=\"#{name}\" href=\"#{
              url}\" class=\"item-small\" target='_blank'>#{listItem}</a></li>"

        html += "</ul><span title=\"Crafting Chance\" class=\"chance\">#{
          chance}%</span></li>"

      html += '</ul>'
    else ''

  _tradeHTML: ->
    """
    <form name="tradeform" method="POST" style="display: inline-block">

      <input type="hidden" name="json">
      <input type="submit" name="submit" value="Search!" style="display: none">

      <select id="tradetype" class="textbox" title="Trade Type">
        <option value="has1">Want</option>
        <option value="wants1">Have</option>
      </select>

      <select id="quality" class="textbox" title="Quality">
        <option value="6">Unique</option>
        <option value="3">Vintage</option>
        <option value="11">Strange</option>
        <option value="1">Genuine</option>
        <option value="14">Collector's</option>
        <option value="13">Haunted</option>
        <option value="5">Unusual</option>
      </select>

    </form>
    """

  _wishlistHTML: ->
    if user.loggedIn
      """
      <div style="display: inline-block;">
      <div id="wishlistmessage"
       style="display: none; margin: 0 0 4px -18px">Added</div>
      <i id="wishlistbutton" class="fa fa-star fa-lg button-icon"
       title="Add to Wishlist"></i>
      </div>
      """
    else ''

  _buttonsHTML: ->
    wikiLink = "https://wiki.teamfortress.com/wiki/#{
      encodeURIComponent @item.name}"

    """
    <div id="buttons">

    <a class="fa fa-info fa-lg button-icon" target="_blank"
     title="Open in Wiki" href="#{wikiLink}"></a>

    <a id="market-btn" class="fa fa-shopping-cart fa-lg button-icon"
     target="_blank" title="Community Market"></a>

    <a id="classifieds-btn" class="fa fa-exchange-alt fa-lg button-icon"
     target="_blank" title="Find Trades"></a>

    #{@_tradeHTML()}
    #{@_wishlistHTML()}
    </div>
    """

  _buyHTML: ->
    # Buy button and store price HTML
    if @item.storePrice
      """
      <div id="buy">
      <form style="display: inline-block">$#{@item.storePrice}<br>
      <input type="text" value="1" size="1" id="quantity" title="Quantity"
       class="textbox" style="text-align: right">
      </form><a href="#" target="_blank" id="buybutton"><img
       src="https://steamcdn-a.akamaihd.net/apps/tf2/btn_buynow.png"
       alt="Buy Now"></a></div>
      """
    else ''

  _nameLink: ->
    linkButton = document.getElementById 'shortlinkbutton'
    link = document.getElementById 'shortlink'

    linkButton.onclick = ->
      if link.style.display is 'none'
        link.style.display = 'inline'
        linkButton.className = linkButton.className.replace 'down', 'up'
        link.getElementsByTagName('input')[0].select()
      else
        link.style.display = 'none'
        linkButton.className = linkButton.className.replace 'up', 'down'

  _pricesLink: ->
    button = document.getElementById 'pricesource'
    prices = document.getElementById 'prices'

    if @sources.length > 1
      button.style.cursor = 'pointer'

      button.onclick = =>
        @_nextPriceSource()

        button.innerHTML = capitalize @source
        prices.innerHTML = @_priceSourceHTML()

      button.onmouseover = ->
        button.style.textShadow = '0 0 10px rgb(196, 241, 128)'

      button.onmouseout = ->
        button.style.textShadow = ''

  _buttonsLink: ->
    (@form.quality.onchange = =>
      market = document.getElementById 'market-btn'
      quality = @form.quality.options[@form.quality.selectedIndex]
        .text.toLowerCase()
        .replace 'unique', 'Unique'
        .replace 'genuine', 'rarity1'
        .replace 'unusual', 'rarity4'
        .replace "collector's", 'collectors'

      market.href = "https://steamcommunity.com/market/search?\
        category_440_Type%5B%5D=any&\
        category_440_Quality%5B%5D=tag_#{quality}&\
        appid=440&q=#{encodeURIComponent @item.name}"

      classifieds = document.getElementById 'classifieds-btn'
      classifieds.href = "https://backpack.tf/classifieds?item=#{
        encodeURIComponent @item.name}&quality=#{@form.quality.value}")()

  _wishlistLink: ->
    # Update wishlist item index
    if user.isOwnPage()
      for wish, idx in document.getElementsByClassName 'item'
        if wish.getAttribute('data-i') is @item.wishIndex
          @item.wishIndex = idx.toString()
          break

    if user.loggedIn
      action = '/wishlist/add'
      button = document.getElementById 'wishlistbutton'

      if user.isOwnPage()
        action = '/wishlist/remove'
        button.title = 'Remove from Wishlist'

      # Add to wishlist or remove from wishlist
      button.onclick = =>
        data = 'index': @item.id, 'quality': @form.quality.value

        if user.isOwnPage()
          data = 'i': @item.wishIndex

        postAjax action, data, (response) =>
          if response is 'Added'
            message = document.getElementById 'wishlistmessage'
            message.style.display = 'block'
            message.className = 'animate__animated animate__fadeInLeft'
            setTimeout (->
              message.className = 'animate__animated animate__fadeOut'), 1000

          else if response is 'Removed'
            @hide()
            @item.elem.parentNode.parentNode.removeChild @item.elem.parentNode

  _buyLink: ->
    button = document.getElementById 'buybutton'
    if button
      quantity = document.getElementById 'quantity'
      (quantity.onchange = =>
        button.href = "https://store.steampowered.com/buyitem/440/#{
          @item.id}/#{quantity.value}")()

  _generate: ->
    # Itembox HTML
    @elem.innerHTML =
      """
      #{@_tagsHTML()}#{@_nameHTML()}#{@_classesHTML()}
      #{@_bundleHTML()}
      #{@_pricesHTML()}
      #{@_blueprintsHTML()}
      #{@_buttonsHTML()}#{@_buyHTML()}
      """

    @form = document.tradeform

    @_nameLink()
    @_pricesLink()
    @_buttonsLink()
    @_wishlistLink()
    @_buyLink()

    # Hover area
    hoverArea = document.createElement 'div'
    hoverArea.id = 'hoverarea'

    if @item.imageURL
      img = document.createElement 'img'
      img.alt = @item.name
      img.src = @item.imageURL
      hoverArea.appendChild img

    # Add hover area to itembox
    @elem.insertBefore hoverArea,
      document.getElementById('blueprints') or
      document.getElementById('buttons')

    # Enable hover box
    new HoverBox(hoverArea, null, @item)

    # Wishlist item quality
    if @item.qualityNo
      @form.quality.value = @item.qualityNo
    # Auto quality selection
    else if @item.prices[@source]
      for option, i in @form.quality.options
        if option.innerHTML of @item.prices[@source]
          @form.quality.selectedIndex = i
          @form.quality.onchange()
          break

class HoverBox
  constructor: (area, @itemBox, @item) ->
    # Allow providing only itemBox
    # Area then becomes all 'item' elements
    if area instanceof ItemBox
      @itemBox = area
      area = null

    @elem = document.getElementById 'hoverbox'

    unless @elem
      @elem = document.createElement 'div'
      @elem.id = 'hoverbox'
      document.body.appendChild @elem

    @_add(area)

  _add: (area) ->
    list = if area then [area] else document.getElementsByClassName 'item'

    for item in list
      item.addEventListener 'mouseout', @_hide, false
      item.addEventListener 'mousemove', @_moveMouse, false
      item.addEventListener 'mouseover', @_show, false
      if @itemBox
        item.addEventListener 'click', @_clickItem, false

    if @itemBox
      # iOS doesn't support 'click' on document
      for event in ['click', 'touchend']
        document.addEventListener event, @_hideItemBox, false
      document.onkeydown = (e) => @itemBox.hide() if e.keyCode is 27

  _show: (e) =>
    item = @item or new Item e.currentTarget
    description = escapeHTML item.description

    if description
      if 'bundle' in item.tags and description.indexOf('---') isnt -1
        descList = description.split '---'
        description =
          """
          #{descList[0]}
          <span style="color: #95af0c">#{descList[1]}</span>
          """

    @elem.innerHTML =
      """
      <div class="name">#{
      item.name}</div><span class="level">#{item.level}</span>#{
      item.attributes}<div class="desc">#{description}</div>
      """

    @elem.style.display = 'block'

  _hide: =>
    @elem.style.display = 'none'

  _hideItemBox: (e) =>
    el = e.target
    if el.className isnt 'item'
      els = []
      while el
        els.push el
        el = el.parentNode

      @itemBox.hide() if @itemBox.elem not in els

  _moveMouse: (e) =>
    @elem.style.top = "#{e.pageY + 28}px"
    @elem.style.left = "#{e.pageX - 154}px"

  _clickItem: (e) =>
    @itemBox.show new Item e.currentTarget
    e.preventDefault()
    e.stopPropagation()

capitalize = (word) ->
  word[0].toUpperCase() + word[1...]

escapeHTML = (string) ->
  string.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

getCookie = (name) ->
  cookies = document.cookie.split ';'

  for cookie in cookies
    cookie = cookie[1...] while cookie[0] is ' '
    return cookie[name.length + 1...] if cookie[...name.length] is name

setCookie = (name, value, days) ->
  expires = ''

  if days
    date = new Date
    date.setDate(date.getDate() + days)
    expires = ";expires=#{date.toUTCString()}"

  document.cookie = "#{name}=#{value}#{expires}"

ajax = (url, callback) ->
  request = _getAjaxRequest(callback)
  request.open 'GET', url, true
  request.setRequestHeader 'X-Requested-With', 'XMLHttpRequest'
  request.send()

postAjax = (url, data, callback) ->
  request = _getAjaxRequest(callback)
  request.open 'POST', url, true
  request.setRequestHeader 'Content-Type',
                           'application/x-www-form-urlencoded'

  request.send ("#{name}=#{value}" for name, value of data).join('&')

_getAjaxRequest = (callback) ->
  request = new XMLHttpRequest

  request.onreadystatechange = ->
    if request.readyState is 4 and request.status is 200
      callback request.responseText

  return request

root.user = new User

root.Item = Item
root.ItemBox = ItemBox
root.HoverBox = HoverBox
