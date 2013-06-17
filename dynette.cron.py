#!/usr/bin/python

import os
import sys
import json
from urllib import urlopen

conf_file = '/etc/bind/named.conf.local'    # Include this filename in '/etc/bind/named.conf'
zone_dir  = '/var/named/data/'              # Do not forget the trailing '/'
subs_urls = ['http://dyndns.yunohost.org']  # 127.0.0.1 if you install subscribe server locally
ns1       = 'dynhost.yunohost.org'          # Name servers
ns2       = 'hostmaster.yunohost.org'

allowed_operations = {
            '.'                  : ['A', 'TXT', 'MX'],
            'pubsub.'            : ['A'],
            'muc.'               : ['A'],
            'vjud'               : ['A'],
            '_xmpp-client._tcp.' : ['SRV'],
            '_xmpp-server._tcp.' : ['SRV']
}
            


lines = []
for url in subs_urls:
    domains = json.loads(str(urlopen(url +'/domains').read()))

    for domain in domains:
        result = json.loads(str(urlopen(url +'/all/'+ domain).read()))
	if not os.path.exists(zone_dir + domain +'.db'):
            db_lines = [
                '$ORIGIN .',
                '$TTL 10 ; 10 seconds',
                domain+'.   IN SOA  '+ ns1 +'. '+ ns2 +'. (',
                '                                18         ; serial',
                '                                10800      ; refresh (3 hours)',
                '                                3600       ; retry (1 hour)',
                '                                604800     ; expire (1 week)',
                '                                10         ; minimum (10 seconds)',
                '                                )',
                '$TTL 3600       ; 1 hour',
                '                        NS      '+ ns1 +'.',
                '                        NS      '+ ns2 +'.',
                '',
                '$ORIGIN '+ domain +'.',
            ]
            with open(zone_dir + domain +'.db', 'w') as zone:
                for line in db_lines:
                    zone.write(line + '\n')
        lines.extend([
                'zone "'+ domain +'" {',
                '   type master;',
                '   file "'+ zone_dir + domain +'.db"; ',
                '   update-policy {',
        ])

        for entry in result:
            for subd, type in allowed_operations.items():
                if subd == '.': subd = ''
                lines.append('       grant '+ entry['subdomain'] +'. name '+ subd + entry['subdomain'] +'. ' + ' '.join(type) +';')

        lines.extend([
                '   };',
                '};',
        ])

        for entry in result:
            lines.extend([
                'key '+ entry['subdomain'] +'. {',
                '       algorithm hmac-md5;',
                '       secret "'+ entry['public_key'] +'";',
                '};',
            ])


os.system('cp '+ conf_file +' '+ conf_file +'.back')

with open(conf_file, 'w') as zone:
    for line in lines:
        zone.write(line + '\n')

os.system('chown -R bind:bind '+ zone_dir +' '+ conf_file)
if os.system('rndc reload') == 0:
    exit(0)
else:
    os.system('cp '+ conf_file +' '+ conf_file +'.bad')
    os.system('cp '+ conf_file +'.back '+ conf_file)
    os.system('rndc reload')
    print("An error occured ! Please check daemon.log and your conf.bad")
    exit(1)
