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

  # Market price HTML
  marketPrice = item.getAttribute('data-marketprice') or ''
  if marketPrice
    marketPrice = marketPrice.replace(/[{}']/g,'').replace(/, /g,'<br>')
    for i in ['Unique','Vintage','Strange','Genuine','Haunted']
      re = new RegExp(i,"g")
      marketPrice = marketPrice
                .replace(re,"<span class='#{ i.toLowerCase() }'>#{ i }</span>")
    marketPrice = "<h3 id='marketprice'>#{ marketPrice }</h3>"

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
            name = name.replace('Any ','').replace('Spy Watch','PDA2')
            if name.split(' ').length > 2
              name = name.replace('Weapon','Set')
            url = "/search?q=#{ encodeURIComponent(name) }"

          listItem = "<a href=\"#{ url }\" target='_blank'>#{ listItem }</a>"
          blueprintsHTML += listItem

      blueprintsHTML += "<div title='Crafting Chance'
   style='position:relative;top: 13px;margin-left:420px;'>
  <h3>#{ chance }%</h3></div></div>"

    blueprintsHTML += '</div>'

  # Buy button and price HTML
  buyHTML = if storePrice then "<form
 style='position:absolute;bottom:19px;left:345px;'>
$#{ storePrice }<br>
<input type='text' value='1' size='1' id='quantity'
 class='textbox'>
</form><a href='#' id='buybutton'></a>" else ''

  # Classes HTML
  classesHTML = "<div id='classes' style='position:absolute;top:0;right:0'>"
  classes = item.getAttribute('data-classes')
  if classes
    for i in classes.split(',')
      classesHTML += "<a href='/search?q=#{ i }' target='_blank'>
<img title='#{ i }' width='40px' height='40px'
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

    for i in ['hat','misc']
      if i in tags
        title = capitalize(i)
        image = i

    if isToken and classes
      title = 'Class Token'
      image = 'class_token'

    if title and image
      tagsHTML += "<a href='/search?q=#{ title }' target='_blank'>
<img title='#{ title }' width='50px' height='50px'
 src='/images/items/#{ image }.png'></a><br>"
  tagsHTML += "</div>"

  itemName = item.title
  if link
    itemName = "<a href='/item/#{ item.id }'
 target='_blank' class='glow' title='Go to Item Page'>
#{ itemName }</a>"

  wikiLink = "http://wiki.teamfortress.com/wiki/#{ item.title }"

  # Itembox HTML
  itemBox.innerHTML = "
<h2 id='itemname'>#{ itemName }</h2>
<a class='button' target='_blank' title='Open in Wiki'
 style='position:absolute;bottom:10px;left:10px;'
 href=\"#{ wikiLink }\">Wiki</a>
#{ marketPrice }
<form name='tf2outpostform' method='POST'
 action='http://www.tf2outpost.com/search'>

<input type='hidden' name='has1'>
<input class='button'
 style='position:absolute;bottom:10px;left:70px;margin:0;'
 type='submit'
 title='Find Trades' name='submit' value='Trades'>

<input type='hidden' name='type' value='any'>
<select id='quality' class='textbox' style='text-align:left'>
  <option value='6'>Unique</option>
  <option value='3'>Vintage</option>
  <option value='11'>Strange</option>
  <option value='1'>Genuine</option>
  <option value='13'>Haunted</option>
  <option value='5'>Unusual</option>
</select>

</form>
#{ buyHTML }
#{ blueprintsHTML }
#{ classesHTML }
#{ tagsHTML }
"

  # Hover area
  hoverArea = document.createElement('div')
  hoverArea.title = item.title
  hoverArea.setAttribute('data-description', getDescription(item))
  hoverArea.setAttribute('data-tags', tags)
  hoverArea.id = 'hoverarea'
  hoverArea.style.backgroundImage = "url('#{ imageUrl }')"
  hoverArea.innerHTML = "<div style='display:none'>
#{ getAttributes(item) }</div>"
  hoverArea.addEventListener("mouseout", hide, false)
  hoverArea.addEventListener("mousemove", moveMouse, false)
  hoverArea.addEventListener("mouseover", show, false)
  itemBox.appendChild(hoverArea)

  # Buy button link
  buyButton = document.getElementById('buybutton')
  if buyButton
    buyButton.onclick = ->
      quantity = document.getElementById('quantity').value
      window.open("http://store.steampowered.com/buyitem/440/
#{ item.id }/#{ quantity }")

  # TF2Outpost link
  quality = document.tf2outpostform.quality
  quality.onchange = ->
    document.tf2outpostform.has1.value = "440,#{ item.id },#{ quality.value }"

  if itemName.indexOf('Strange Part') == -1
    # Auto quality selection
    for option, i in quality.options
      if marketPrice.indexOf(option.innerHTML) != -1
        quality.selectedIndex = i
        break

  # Update the quality selection
  quality.onchange()
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
