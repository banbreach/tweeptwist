#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# twitwist
#
# Generate and resolve twitter handle variations to detect typo squatting,
# phishing and corporate espionage.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'Banbreach'
__version__ = '0.01'
__email__ = 'contact@banbreach.com'

import config
import sys
import re
import math
import json
import tweepy
import signal
import argparse
import time
from datetime import date
import datetime
from dateutil.relativedelta import relativedelta
from random import randint
import threading

try:
    import queue
except ImportError:
    import Queue as queue



THREAD_COUNT_DEFAULT = 10

if sys.platform != 'win32' and sys.stdout.isatty():
         FG_RND = '\x1b[3%dm' % randint(1, 8)
         FG_RED = '\x1b[31m'
         FG_YEL = '\x1b[33m'
         FG_GRE = '\x1b[32m'
         FG_MAG = '\x1b[35m'
         FG_CYA = '\x1b[36m'
         FG_BLU = '\x1b[34m'
         FG_RST = '\x1b[39m'
         ST_BRI = '\x1b[1m'
         ST_RST = '\x1b[0m'
else:
         FG_RND = ''
         FG_RED = ''
         FG_YEL = ''
         FG_GRE = ''
         FG_MAG = ''
         FG_CYA = ''
         FG_BLU = ''
         FG_RST = ''
         ST_BRI = ''
         ST_RST = ''

def is_username(name):
    return all((char >= '0' and char <= '9')
            or (char >= 'a' and char <= 'z') 
            or (char >= 'A' and char <= 'Z')
            or char == '_' for char in name)

def handle_none(x):
    return '' if x is None else x

def sigint_handler(signal, frame):
    sys.stdout.write('\nStopping threads... ')
    sys.stdout.flush()
    for worker in threads:
        worker.stop()
    time.sleep(1)
    sys.stdout.write('Done\n')
    bye(0)

def bye(code):
    sys.stdout.write(FG_RST + ST_RST)
    sys.exit(code)

def p_cli(data):
    global args
    if not args.fmt or args.fmt == 'o':
        sys.stdout.write(data.encode('utf-8'))
        sys.stdout.flush()

def p_csv(data):
    global args
    if args.fmt == 'c':
        sys.stdout.write(data.encode('utf-8'))

def p_json(data):
    global args
    if args.fmt == 'j':
        sys.stdout.write(data)

def p_info():
    p_cli(FG_RND + ST_BRI +
'''
 _                           _            _     _   
| |                         | |          (_)   | |  
| |___      _____  ___ _ __ | |___      ___ ___| |_ 
| __\ \ /\ / / _ \/ _ \ '_ \| __\ \ /\ / / / __| __|
| |_ \ V  V /  __/  __/ |_) | |_ \ V  V /| \__ \ |_ 
 \__| \_/\_/ \___|\___| .__/ \__| \_/\_/ |_|___/\__| {%s}
                      | |                         
                      |_|                         
''' % __version__ + FG_RST + ST_RST)

def humanize(number):
    idx = 0 if not number else int(math.floor(math.log10(number)/3))
    num = number / (10 ** (3 * idx))
    return '{:.0f}{}'.format(num, ['','K', 'M'][idx])

def humanize_date(created_at):
    #rd = relativedelta(date.today(), created_at)
    if created_at > 365:
        return str(created_at / 365) + 'y'
    if created_at > 30:
        return str(created_at / 30) + 'm'
    return str(created_at) + 'd'

def humanize_source(src):
    d = {u'Twitter Web Client':'Desktop', u'Twitter for iPhone':'iPhone', u'Twitter for Android':'Android', u'Twitter for BlackBerry®':'BlackBerry', u'Mobile Web':'Mobile'}
    if src in d:
        return d[ src ]
    return src if src else '-'

def age_in_days(dt):
    td = (datetime.date.today() - dt.date())
    return td.days

class DomainThread(threading.Thread):

        def __init__(self, queue, api):
            threading.Thread.__init__(self)
            self.jobs = queue
            self.kill_received = False
            self.api = api

        def stop(self):
            self.kill_received = True

        def run(self):
            while not self.kill_received:
                domain = self.jobs.get()
                try:
                    u = self.api.raw_user(domain[ 'domain-name' ])
                    domain[ 'id' ] = u.id
                    domain[ 'tweets' ] = u.statuses_count
                    domain[ 'friends' ] = u.friends_count
                    domain[ 'followers' ] = u.followers_count
                    domain[ 'age' ] = age_in_days(u.created_at)
                    domain[ 'verified' ] = u.verified
                    # Tweepy User.status: Nullable
                    if hasattr(u, 'status'):
                        domain[ 'message' ] = u.status.text
                        domain[ 'source' ] = u.status.source
                    else:
                        domain[ 'message' ] = '-'
                        domain[ 'source' ] = '-'
                    # User.location : Nullable
                    # User.utc_offset: Nullable
                    # User.time_zone: Nullable
                    domain[ 'place' ] = u.geo_enabled                  \
                            or u.location or u.profile_location         \
                            or u.time_zone or u.utc_offset              \
                        or (hasattr(u, 'status') and (u.status.coordinates or u.status.place))
                    if not domain[ 'place' ] or isinstance(domain[ 'place' ], bool): # isinstance required to handle cases like place: True
                        domain[ 'place' ] = '-' 
                    domain[ 'locale' ] = u.lang or (hasattr(u, 'status') and u.status.lang)
                except tweepy.TweepError:
                    pass
                except:
                    pass
                self.jobs.task_done()


def run(domains):
    api = TwClient()
    for domain in domains:
        try:
            u = api.raw_user(domain[ 'domain-name' ])
            domain[ 'id' ] = u.id
            domain[ 'tweets' ] = u.statuses_count
            domain[ 'friends' ] = u.friends_count
            domain[ 'followers' ] = u.followers_count
            domain[ 'age' ] = age_in_days(u.created_at)
            domain[ 'verified' ] = u.verified
            # Tweepy User.status: Nullable
            if hasattr(u, 'status'):
                domain[ 'message' ] = u.status.text
                domain[ 'source' ] = u.status.source
            else:
                domain[ 'message' ] = '-'
                domain[ 'source' ] = '-'
            # User.location : Nullable
            # User.utc_offset: Nullable
            # User.time_zone: Nullable
            domain[ 'place' ] = u.geo_enabled                  \
                    or u.location or u.profile_location         \
                    or u.time_zone or u.utc_offset              \
                    or (hasattr(u, 'status') and (u.status.coordinates or u.status.place))
            if not domain[ 'place' ] or isinstance(domain[ 'place' ], bool): # isinstance required to handle cases like place: True
                domain[ 'place' ] = '-' 
            domain[ 'locale' ] = u.lang or (hasattr(u, 'status') and u.status.lang)
        except tweepy.TweepError:
            pass

def generate_json(domains):
    json_domains = domains
    for domain in json_domains:
        domain['domain-name'] = domain['domain-name'].lower()
        domain['fuzzer'] = domain['fuzzer'].lower()

    return json.dumps(json_domains, indent=4, sort_keys=True)

def generate_csv(domains):
    output = u'fuzzer,domain-name,tweets,friends,followers,age,verified,source,place,locale,message\n'

    for domain in domains:
        #print 'processing %s' % domain
        output += u'%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (domain.get('fuzzer'),
        domain.get('domain-name'),
        handle_none(domain.get('tweets')),
        handle_none(domain.get('friends')),
        handle_none(domain.get('followers')),
        handle_none(domain.get('age')),
        handle_none(domain.get('verified')),
        handle_none(domain.get('source')),
        handle_none(domain.get('place')),
        handle_none(domain.get('locale')),
        '"' + handle_none(domain.get('message')) + '"') # quoting tweets is necessary to prevent CSV parsers from breaking

    return output

def generate_cli(domains):
    output = ''

    width_fuzzer = max([len(d['fuzzer']) for d in domains]) + 1
    width_domain = max([len(d['domain-name']) for d in domains]) + 1
    width_source = max([len(d['source']) for d in domains]) + 1
    # Fix None handling
    width_place = max([len(d['place']) for d in domains]) + 1
     
    for domain in domains:
        info = ''
        if 'id' in domain:
            info += '%s%s%s' % (FG_MAG, humanize(domain[ 'tweets' ]).rjust(5), FG_RST) 
            info += '%s%s%s' % (FG_MAG, humanize(domain[ 'friends' ]).rjust(5), FG_RST) 
            info += '%s%s%s' % (FG_MAG, humanize(domain[ 'followers' ]).rjust(5), FG_RST) 
            info += '%s%s%s' % (FG_RED, humanize_date(domain[ 'age' ]).rjust(5), FG_RST) 
            info += '  ' # add space for ladjust
            info += '%s%s%s' % (FG_BLU, str(domain[ 'verified' ]).ljust(6), FG_RST) 
            info += '%s%s%s' % (FG_MAG, domain[ 'source' ].rjust(width_source), FG_RST) 
            info += '%s%s%s' % (FG_GRE, unicode(domain[ 'place' ]).rjust(width_place), FG_RST) 
            info += '  ' # add space for ladjust
            info += '%s%s%s' % (FG_RED, domain[ 'locale' ].rjust(4), FG_RST) 
            info += '  ' # add space for ladjust
            info += '%s%s%s' % (FG_MAG, domain[ 'message' ][:20].ljust(24), FG_RST) 

        if not info:
            info = '-'
        output += '%s%s%s %s %s\n' % (FG_CYA, domain['fuzzer'].ljust(width_fuzzer), FG_RST, domain['domain-name'].ljust(width_domain), info)

    return output


class DomainFuzz():

    def __init__(self, domain):
        self.domain  = domain #, self.tld = self.__domain_tld(domain)
        self.domains = []
        self.qwerty = {
        '1': '2q', '2': '3wq1', '3': '4ew2', '4': '5re3', '5': '6tr4', '6': '7yt5', '7': '8uy6', '8': '9iu7', '9': '0oi8', '0': 'po9',
        'q': '12wa', 'w': '3esaq2', 'e': '4rdsw3', 'r': '5tfde4', 't': '6ygfr5', 'y': '7uhgt6', 'u': '8ijhy7', 'i': '9okju8', 'o': '0plki9', 'p': 'lo0',
        'a': 'qwsz', 's': 'edxzaw', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'yhbvft', 'h': 'ujnbgy', 'j': 'ikmnhu', 'k': 'olmji', 'l': 'kop',
        'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
        }
        self.qwertz = {
        '1': '2q', '2': '3wq1', '3': '4ew2', '4': '5re3', '5': '6tr4', '6': '7zt5', '7': '8uz6', '8': '9iu7', '9': '0oi8', '0': 'po9',
        'q': '12wa', 'w': '3esaq2', 'e': '4rdsw3', 'r': '5tfde4', 't': '6zgfr5', 'z': '7uhgt6', 'u': '8ijhz7', 'i': '9okju8', 'o': '0plki9', 'p': 'lo0',
        'a': 'qwsy', 's': 'edxyaw', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'zhbvft', 'h': 'ujnbgz', 'j': 'ikmnhu', 'k': 'olmji', 'l': 'kop',
        'y': 'asx', 'x': 'ysdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
        }
        self.azerty = {
        '1': '2a', '2': '3za1', '3': '4ez2', '4': '5re3', '5': '6tr4', '6': '7yt5', '7': '8uy6', '8': '9iu7', '9': '0oi8', '0': 'po9',
        'a': '2zq1', 'z': '3esqa2', 'e': '4rdsz3', 'r': '5tfde4', 't': '6ygfr5', 'y': '7uhgt6', 'u': '8ijhy7', 'i': '9okju8', 'o': '0plki9', 'p': 'lo0m',
        'q': 'zswa', 's': 'edxwqz', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'yhbvft', 'h': 'ujnbgy', 'j': 'iknhu', 'k': 'olji', 'l': 'kopm', 'm': 'lp',
        'w': 'sxq', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhj'
        }
        self.keyboards = [ self.qwerty, self.qwertz, self.azerty ]


    def __validate_domain(self, domain):
        #allowed = re.compile('^[\w]+', re.IGNORECASE)
        return len(domain) < 16 and is_username(domain)

    def __filter_domains(self):
        seen = set()
        filtered = []

        for d in self.domains:
            #if not self.__validate_domain(d['domain-name']):
                #p_err("debug: invalid domain %s\n" % d['domain-name'])
            name_lowercase = d[ 'domain-name' ].lower()
            if self.__validate_domain(d['domain-name']) and name_lowercase not in seen:
                # Twitter usernames are case-insensitive
                seen.add(name_lowercase)
                filtered.append(d)

        #p_cli('unique domain names seen %d, filtered %d\n' % (len(seen), len(filtered)))
        self.domains = filtered

    def __bitsquatting(self):
        result = []
        masks = [1, 2, 4, 8, 16, 32, 64, 128]
        for i in range(0, len(self.domain)):
            c = self.domain[i]
            for j in range(0, len(masks)):
                b = chr(ord(c) ^ masks[j])
                o = ord(b)
                if (o >= 48 and o <= 57) or (o >= 97 and o <= 122) or o == 45:
                    result.append(self.domain[:i] + b + self.domain[i+1:])

        return result

    def __homoglyph(self):
        glyphs = {
        'a': [u'à', u'á', u'â', u'ã', u'ä', u'å', u'ɑ', u'а', u'ạ', u'ǎ', u'ă', u'ȧ', u'ӓ'],
        'b': ['d', 'lb', 'ib', u'ʙ', u'Ь', u'b̔', u'ɓ', u'Б'],
        'c': [u'ϲ', u'с', u'ƈ', u'ċ', u'ć', u'ç'],
        'd': ['b', 'cl', 'dl', 'di', u'ԁ', u'ժ', u'ɗ', u'đ'],
        'e': [u'é', u'ê', u'ë', u'ē', u'ĕ', u'ě', u'ė', u'е', u'ẹ', u'ę', u'є', u'ϵ', u'ҽ'],
        'f': [u'Ϝ', u'ƒ', u'Ғ'],
        'g': ['q', u'ɢ', u'ɡ', u'Ԍ', u'Ԍ', u'ġ', u'ğ', u'ց', u'ǵ', u'ģ'],
        'h': ['lh', 'ih', u'һ', u'հ', u'Ꮒ', u'н'],
        'i': ['1', 'l', u'Ꭵ', u'í', u'ï', u'ı', u'ɩ', u'ι', u'ꙇ', u'ǐ', u'ĭ'],
        'j': [u'ј', u'ʝ', u'ϳ', u'ɉ'],
        'k': ['lk', 'ik', 'lc', u'κ', u'ⲕ', u'κ'],
        'l': ['1', 'i', u'ɫ', u'ł'],
        'm': ['n', 'nn', 'rn', 'rr', u'ṃ', u'ᴍ', u'м', u'ɱ'],
        'n': ['m', 'r', u'ń'],
        'o': ['0', u'Ο', u'ο', u'О', u'о', u'Օ', u'ȯ', u'ọ', u'ỏ', u'ơ', u'ó', u'ö', u'ӧ'],
        'p': [u'ρ', u'р', u'ƿ', u'Ϸ', u'Þ'],
        'q': ['g', u'զ', u'ԛ', u'գ', u'ʠ'],
        'r': [u'ʀ', u'Г', u'ᴦ', u'ɼ', u'ɽ'],
        's': [u'Ⴝ', u'Ꮪ', u'ʂ', u'ś', u'ѕ'],
        't': [u'τ', u'т', u'ţ'],
        'u': [u'μ', u'υ', u'Ս', u'ս', u'ц', u'ᴜ', u'ǔ', u'ŭ'],
        'v': [u'ѵ', u'ν', u'v̇'],
        'w': ['vv', u'ѡ', u'ա', u'ԝ'],
        'x': [u'х', u'ҳ', u'ẋ'],
        'y': [u'ʏ', u'γ', u'у', u'Ү', u'ý'],
        'z': [u'ʐ', u'ż', u'ź', u'ʐ', u'ᴢ']
        }

        result = []

        for ws in range(0, len(self.domain)):
            for i in range(0, (len(self.domain)-ws)+1):
                win = self.domain[i:i+ws]

                j = 0
                while j < ws:
                    c = win[j]
                    if c in glyphs:
                        win_copy = win
                        for g in glyphs[c]:
                            win = win.replace(c, g)
                            result.append(self.domain[:i] + win + self.domain[i+ws:])
                            win = win_copy
                    j += 1

        return list(set(result))

    def __hyphenation(self):
        result = []

        for i in range(1, len(self.domain)):
            result.append(self.domain[:i] + '-' + self.domain[i:])

        return result

    def __underscore(self):
        result = []

        result.append('_' + self.domain)
        for i in range(1, len(self.domain)):
            result.append(self.domain[:i] + '_' + self.domain[i:])
        result.append(self.domain + '_')

        return result

    def __insertion(self):
        result = []

        for i in range(1, len(self.domain)-1):
            for keys in self.keyboards:
                if self.domain[i] in keys:
                    for c in keys[self.domain[i]]:
                        result.append(self.domain[:i] + c + self.domain[i] + self.domain[i+1:])
                        result.append(self.domain[:i] + self.domain[i] + c + self.domain[i+1:])

        return list(set(result))

    def __omission(self):
        result = []

        for i in range(0, len(self.domain)):
            result.append(self.domain[:i] + self.domain[i+1:])

        n = re.sub(r'(.)\1+', r'\1', self.domain)

        if n not in result and n != self.domain:
            result.append(n)

        return list(set(result))

    def __repetition(self):
        result = []

        for i in range(0, len(self.domain)):
            if self.domain[i].isalpha():
                result.append(self.domain[:i] + self.domain[i] + self.domain[i] + self.domain[i+1:])

        return list(set(result))

    def __replacement(self):
        result = []

        for i in range(0, len(self.domain)):
            for keys in self.keyboards:
                if self.domain[i] in keys:
                    for c in keys[self.domain[i]]:
                        result.append(self.domain[:i] + c + self.domain[i+1:])

        return list(set(result))

    def __subdomain(self):
        result = []

        for i in range(1, len(self.domain)):
            if self.domain[i] not in ['-', '.'] and self.domain[i-1] not in ['-', '.']:
                result.append(self.domain[:i] + '.' + self.domain[i:])

        return result

    def __transposition(self):
        result = []

        for i in range(0, len(self.domain)-1):
            if self.domain[i+1] != self.domain[i]:
                result.append(self.domain[:i] + self.domain[i+1] + self.domain[i] + self.domain[i+2:])

        return result

    def __vowel_swap(self):
        vowels = 'aeiou'
        result = []

        for i in range(0, len(self.domain)):
            for vowel in vowels:
                if self.domain[i] in vowels:
                    result.append(self.domain[:i] + vowel + self.domain[i+1:])

        return list(set(result))

    def __addition(self):
        result = []

        for i in range(97, 123):
            result.append(self.domain + chr(i))

        return result

    def generate(self):
        self.domains.append({ 'fuzzer': 'Original*', 'domain-name': self.domain })

        for domain in self.__addition():
            self.domains.append({ 'fuzzer': 'Addition', 'domain-name': domain })
        for domain in self.__bitsquatting():
            self.domains.append({ 'fuzzer': 'Bitsquatting', 'domain-name': domain })
        for domain in self.__homoglyph():
            self.domains.append({ 'fuzzer': 'Homoglyph', 'domain-name': domain })
        for domain in self.__underscore():
            self.domains.append({ 'fuzzer': 'Underscoring', 'domain-name': domain })
        for domain in self.__insertion():
            self.domains.append({ 'fuzzer': 'Insertion', 'domain-name': domain })
        for domain in self.__omission():
            self.domains.append({ 'fuzzer': 'Omission', 'domain-name': domain })
        for domain in self.__repetition():
            self.domains.append({ 'fuzzer': 'Repetition', 'domain-name': domain })
        for domain in self.__replacement():
            self.domains.append({ 'fuzzer': 'Replacement', 'domain-name': domain })
        #for domain in self.__subdomain():
        #   self.domains.append({ 'fuzzer': 'Subdomain', 'domain-name': domain })
        for domain in self.__transposition():
            self.domains.append({ 'fuzzer': 'Transposition', 'domain-name': domain })
        for domain in self.__vowel_swap():
            self.domains.append({ 'fuzzer': 'Vowel-swap', 'domain-name': domain })

        self.__filter_domains()

class TwClient():

    def __init__(self):
        self.auth = tweepy.OAuthHandler(config.consumer_key, config.consumer_secret)
        self.auth.set_access_token(config.access_token, config.access_token_secret)
        self.api = tweepy.API(auth_handler = self.auth, wait_on_rate_limit=True)

    def raw_user(self, user):
        return self.api.get_user(screen_name = user)

def main():
    signal.signal(signal.SIGINT, sigint_handler)
    #signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    parser = argparse.ArgumentParser(
    usage='%s [OPTION]... DOMAIN' % sys.argv[0],
    add_help = True,
    description=
    '''Find Twitter usernames that scammers may use to attack you. '''
    '''Can detect typosquatters, bitsquatters, and brandjacking. '''
    )

    parser.add_argument('domain', help='username to check with or without the leading `@` i.e @jack and jack both work')
    out_fmt_group = parser.add_mutually_exclusive_group()
    out_fmt_group.add_argument('-c', '--csv', action='store_const', dest='fmt', const='c', help='print output in CSV format')
    out_fmt_group.add_argument('-j', '--json', action='store_const', dest='fmt', const='j',help='print output in JSON format')
    out_fmt_group.add_argument('-o', '--stdout', action='store_const', dest='fmt', const='o', default = 'o', help='print to stdout')

    parser.add_argument('-a', '--all', action='store_true', help='show all generated usernames')
    parser.add_argument('-q', '--quiet', action='store_true', help='suppress banner and version info')
    parser.add_argument('-k', '--key', type=str, help='key to perform sort on (default: %(default)s)', default='age', choices=['domain-name', 'tweets','followers','friends','age'])
    parser.add_argument('-r', '--reverse', action='store_true', help='reverse sort order')
    parser.add_argument('-t', '--threads', type=int, metavar='NUMBER', default=THREAD_COUNT_DEFAULT, help='start specified NUMBER of threads (default: %d)' % THREAD_COUNT_DEFAULT)
    parser.add_argument('-d', '--dry', action='store_true', help='dry run: print number of variations to be checked and exit')

    if len(sys.argv) < 2:
        sys.stdout.write('%stweeptwist %s by <%s>%s\n\n' % (ST_BRI, __version__, __email__, ST_RST))
        parser.print_help()
        bye(0)

    global args
    args = parser.parse_args()

    if not args.quiet:
        p_info()

    username = args.domain
    if args.domain[ 0 ] == '@':
        username = args.domain[1:]

    dfuzz = DomainFuzz(username)
    dfuzz.generate()
    domains = dfuzz.domains

    p_cli('Processing %d username variants' % len(domains))

    if args.dry:
        p_cli('\n')
        bye(0)
    
    jobs = queue.Queue()

    global threads
    threads = []

    for i in range(len(domains)):
        jobs.put(domains[i])

    api = TwClient()
    for i in range(args.threads):
        worker = DomainThread(jobs, api)
        #worker.setDaemon(True)
        worker.start()
        threads.append(worker)


    qperc = 0
    bar = ''
    while not jobs.empty():
        #p_cli('.')
        qcurr = 100 * (len(domains) - jobs.qsize()) / len(domains)
        if qcurr - 5 >= qperc:
            qperc = qcurr
            bar = ('=' * int(qperc * 20/100)).ljust(20)
            p_cli('\rProcessing %d username variants [%s] %u%%' % (len(domains), bar, qperc))
        time.sleep(1/40)

    for worker in threads:
        worker.stop()

    p_cli('\rProcessing %d username variants [%s] %u%%' % (len(domains), bar, qperc))
    hits_total = sum('id' in d for d in domains)
    hits_percent = 100 * hits_total / len(domains)
    p_cli(' %d hits (%d%%)\n\n' % (hits_total, hits_percent))
    time.sleep(1/40)
    #run(domains)

    if not args.all:
        domains_registered = []
        for d in domains:
            if 'id' in d:
                domains_registered.append(d)

        domains = domains_registered
        del domains_registered
    else:
        args.key = 'domain-name'

    domains = sorted(domains, key = lambda x: x[ args.key ], reverse = args.reverse)

    if domains:
        if args.fmt == 'c':
            p_csv(generate_csv(domains))
        elif args.fmt == 'j':
            p_json(generate_json(domains))
        else:
            p_cli(generate_cli(domains))

if __name__=="__main__":
    main()
