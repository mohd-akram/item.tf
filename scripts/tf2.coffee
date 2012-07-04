show = (e) ->
  hbox.innerHTML = e.target.firstChild.innerHTML
  hbox.style.display = "block"

hide = ->
  hbox.style.display = "none"

hideitembox = (e) ->
  target = e.target or e.srcElement
  if target != itembox and target not in itembox.childNodes and target.tagName not in ['LI','A','INPUT']
    itembox.style.display='none'

moveMouse = (e) ->
  hbox.style.top = (e.pageY + 28) + "px"
  hbox.style.left = (e.pageX - 154) + "px"

openSummary = (e) ->
  itemId = e.target.id
  itemName = e.target.firstChild.innerHTML

  marketprice = e.target.getAttribute('data-marketprice').replace(/[{}']/g,'').replace(/, /g,'<br>')
  storeprice = e.target.getAttribute('data-storeprice')

  if storeprice
    storeprice = "$#{ storeprice }"
    buyButton = "<h3>#{ storeprice }</h3><a id='buy-button' href='http://store.steampowered.com/buyitem/440/#{ itemId }'></a>"
  else
    buyButton = ''

  itembox.innerHTML = "<h2>#{ itemName }</h2>
    <a class='button' target='_blank' style='position:absolute;bottom:10px;left:10px;' href='http://wiki.teamfortress.com/wiki/#{ itemName }'>Open in Wiki</a>
    <h3>#{ marketprice }</h3>
    <form name='tf2outpostform' method='POST' action='http://www.tf2outpost.com/search' target='_blank'>
      <input type='hidden' name='has1' value='440,#{ itemId },6'>
      <input class='button' style='position:absolute;bottom:10px;left:140px;' type='submit' name='submit' value='Find trades'>
      <input type='hidden' name='type' value='any'>
    </form>
    #{ buyButton }"

  itembox.style.display = "block"
  imageUrl = e.target.lastChild.innerHTML
  itembox.style.backgroundImage = "url('#{ imageUrl }')"
  #url = window.location.pathname
  #window.open(url[...-6] + 'item/' + e.target.id)

window.onload = ->
  window.hbox = document.getElementById("hoverbox")
  window.itembox = document.getElementById("itembox")

  if hbox
    icells = document.getElementsByTagName("li")
    for cell in icells
      cell.addEventListener("mouseout", hide, false)
      cell.addEventListener("mousemove", moveMouse, false)
      cell.addEventListener("mouseover", show, false)
      cell.addEventListener("click", openSummary, false)

  document.addEventListener("click",hideitembox, false)
