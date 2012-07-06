import re
import os
from urllib.request import urlopen

paints = [7511618, 4345659, 5322826, 14204632, 8208497, 13595446, 10843461, 12955537, 6901050, 8154199, 15185211, 8289918, 15132390, 1315860, 12073019, 16738740, 3100495, 8421376, 3329330, 15787660, 15308410, 4732984, 11049612, 3874595, 6637376, 8400928, 12807213, 12377523, 2960676]

url = "http://wiki.teamfortress.com"
folder = 'images/paints'

if not os.path.exists(folder):
    os.makedirs(folder)

for color in paints:
    hexcolor = hex(color)[2:].upper()

    painturl = '{0}/wiki/File:Paint_Can_{1}.png'.format(url,hexcolor)    
    data = urlopen(painturl).read().decode('utf-8')

    relurl = re.findall(r'src="(/w/images/[^"]*png)"',data)[0]

    picture = urlopen(url+relurl).read()

    filename = '{0}/Paint_Can_{1}.png'.format(folder,color)

    with open(filename,'wb') as f:
        f.write(picture)

    print('Downloaded {}'.format(filename))
