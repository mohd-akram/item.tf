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

escapeHTML = (string) ->
  return string.replace(/&/g,'&amp;')
               .replace(/</g,'&lt;')
               .replace(/>/g,'&gt;')

getAttributes = (item) ->
  divs = item.getElementsByTagName('div')
  attributes = if divs.length>0 then divs[0].innerHTML else ''
  return attributes

getDescription = (item) ->
  description = item.getAttribute('data-description')
  description ?= ''
  return description

getTags = (item) ->
  tags = item.getAttribute('data-tags')
  tags ?= ''
  return tags.split(',')

capitalize = (word) ->
  return word[0].toUpperCase() + word[1...]

hide = ->
  hoverBox.style.display = "none"

window.hideItemBox = (e) ->
  a = e.target or e.srcElement
  if a.getAttribute('class') != 'item'
    els = []
    while a
      els.push(a)
      a = a.parentNode

    if itemBox not in els
      itemBox.style.display = 'none'

moveMouse = (e) ->
  hoverBox.style.top = "#{ e.pageY + 28 }px"
  hoverBox.style.left = "#{e.pageX - 154}px"

window.openSummary = (e) ->
  showItemInfo(e.target)
  e.preventDefault()
  e.stopPropagation()

window.showItemInfo = (element) ->
  init()
  itemId = element.id
  itemName = element.title

  # Market price HTML
  marketPrice = element.getAttribute('data-marketprice')
  if marketPrice
    for i in ['Unique','Vintage','Strange','Genuine','Haunted']
      re = new RegExp(i,"g")
      marketPrice = marketPrice
                .replace(/[{}']/g,'')
                .replace(/, /g,'<br>')
                .replace(re,"<span class='#{ i.toLowerCase() }'>#{ i }</span>")
    marketPrice = "<h3 id='marketprice'>#{ marketPrice }</h3>"
  else
    marketPrice = ''

  storePrice = element.getAttribute('data-storeprice')
  imageUrl = element.getAttribute('data-image')
  blueprints = element.getElementsByTagName('ul')

  # Blueprints HTML
  blueprintsHTML = '<div id="blueprints">'
  for b in blueprints
    chance = b.getAttribute('data-chance')

    blueprintsHTML += '<div class="blueprint">'
    for i in b.getElementsByTagName('li')
      for j in [0...i.getAttribute('data-count')]
        name = i.title
        index = i.id
        style = "background-image:url(#{ i.getAttribute('data-image') });"
        listItem =  "<div title=\"#{ name }\" class='item-small'
 style='#{ style }'></div>"
        if index
          url = "/item/#{ index }"
        else
          name = name.replace('Any ','').replace('Spy Watch','PDA2')
          if name.split(' ').length > 2
            name = name.replace('Weapon','Set')
          url = "/search?q=#{ encodeURIComponent(name) }"

        listItem = "<a href=\"#{ url }\" target='_blank'>#{ listItem }</a>"
        blueprintsHTML += listItem

    blueprintsHTML += "<div title='Crafting Chance'
 style='position:relative;top: 13px;margin-left:440px;'>
<h3>#{ chance }%</h3></div></div>"

  blueprintsHTML += '</div>'

  # Buy button and price HTML
  if storePrice
    storePrice = "$#{ storePrice }"
    buyButton = "<form style='position:absolute;bottom:19px;left:345px;'>
#{ storePrice }<br>
<input type='text' value='1' size='1' id='quantity'
 class='textbox'>
</form><a href='#' id='buy-button'></a>"
  else
    buyButton = ''

  # Classes HTML
  classesHTML = "<div id='classes' style='position:absolute;top:0;right:0'>"
  classes = element.getAttribute('data-classes')
  if classes
    for i in classes.split(',')
      classesHTML += "<a href='/search?q=#{ i }' target='_blank'>
<img title='#{ i }' width='40px' height='40px'
 src='/images/items/#{ i }_icon.png'></a><br>"
  classesHTML += "</div>"

  # Tags HTML
  tagsHTML = "<div id='tags' style='position:absolute;top:-5px;left:5px'>"
  tags = getTags(element)
  if tags.length > 0
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

    for i in ['hat','misc']
      if i in tags
        title = capitalize(i)
        image = i

    if isToken and classes != null
      title = 'Class Token'
      image = 'class_token'

    if title and image
      tagsHTML += "<a href='/search?q=#{ title }' target='_blank'>
<img title='#{ title }' width='50px' height='50px'
 src='/images/items/#{ image }.png'></a><br>"
  tagsHTML += "</div>"

  wikiLink = "http://wiki.teamfortress.com/wiki/#{ itemName }"
  # Itembox HTML
  itemBox.innerHTML = "
<h2 id='itemname'>
<a href='/item/#{itemId}'
 target='_blank' class='glow' title='Go to Item Page'>
#{ itemName }</a></h2>
<a class='button' target='_blank' title='Open in Wiki'
 style='position:absolute;bottom:10px;left:10px;'
 href=\"#{ wikiLink }\">Wiki</a>
#{ marketPrice }
<form name='tf2outpostform' method='POST'
 action='http://www.tf2outpost.com/search'>

<input type='hidden' name='has1' value='440,#{ itemId },6'>
<input class='button'
 style='position:absolute;bottom:10px;left:70px;margin:0;'
 type='submit'
 title='Find Trades' name='submit' value='Trades'>

<input type='hidden' name='type' value='any'>
<select id='quality' class='textbox' style='text-align:left'>
  <option value='6' selected=''>Unique</option>
  <option value='3'>Vintage</option>
  <option value='1'>Genuine</option>
  <option value='5'>Unusual</option>
  <option value='11'>Strange</option>
  <option value='13'>Haunted</option>
</select>

</form>
#{ buyButton }
#{ blueprintsHTML }
#{ classesHTML }
#{ tagsHTML }
"
  itemBox.style.display = "block"

  # Hover area
  hoverArea = document.createElement('div')
  hoverArea.title = element.title
  hoverArea.setAttribute('data-description',getDescription(element))
  hoverArea.setAttribute('data-tags',getTags(element))
  hoverArea.id = 'hoverarea'
  hoverArea.style.backgroundImage = "url('#{ imageUrl }')"
  hoverArea.innerHTML = "<div style='display:none'>
#{ getAttributes(element) }</div>"
  hoverArea.addEventListener("mouseout", hide, false)
  hoverArea.addEventListener("mousemove", moveMouse, false)
  hoverArea.addEventListener("mouseover", show, false)
  itemBox.appendChild(hoverArea)

  # Buy button link
  buy = document.getElementById('buy-button')
  if buy
    buy.onclick = ->
      quantity = document.getElementById('quantity').value
      window.open("http://store.steampowered.com/buyitem/440/
#{ itemId }/#{ quantity }")

  # TF2Outpost link
  quality = document.tf2outpostform.quality
  quality.onchange = ->
    document.tf2outpostform.has1.value = "440,#{ itemId },#{ quality.value }"

window.addHoverbox = ->
  init()
  if hoverBox
    for cell in document.getElementsByClassName('item')
      cell.addEventListener("mouseout", hide, false)
      cell.addEventListener("mousemove", moveMouse, false)
      cell.addEventListener("mouseover", show, false)
      cell.addEventListener("click", openSummary, false)

  document.getElementById('container').addEventListener("click",
                                                        hideItemBox,
                                                        false)
  document.onkeydown = (e) ->
    if e.keyCode == 27
      itemBox.style.display = 'none'

window.init = ->
  window.hoverBox = document.getElementById("hoverbox")
  window.itemBox = document.getElementById("itembox")
