                 _                           _            _     _   
                | |                         | |          (_)   | |  
                | |___      _____  ___ _ __ | |___      ___ ___| |_ 
                | __\ \ /\ / / _ \/ _ \ '_ \| __\ \ /\ / / / __| __|
                | |_ \ V  V /  __/  __/ |_) | |_ \ V  V /| \__ \ |_ 
                 \__| \_/\_/ \___|\___| .__/ \__| \_/\_/ |_|___/\__|
                                        | |                         
                                        |_|                         



Wired recently reported a [new scam](https://www.wired.com/story/classic-scam-steals-bitcoin-on-twitter/)
involving cryptocurrency:
> A new version of a classic online scam is percolating on Twitter.
> The scheme itself is pretty straightforward: Attackers make Twitter handles 
> that closely mimic the verified accounts of well-known figures like Elon Musk,
> John McAfee, or Ethereum cofounder Vitalik Buterin. Then they respond to one 
> of those genuine tweets, giving the appearance of having started a thread, in 
> which they claim that they'll send a significant quantity of cryptocurrency 
> (like 2 bitcoin) to anyone who sends a smaller amount of currency (like 0.02 
> bitcoin) to a particular wallet. 

The issue was (as far as we can tell) first reported by [@TinkerSec](https://twitter.com/TinkerSec).
A screengrab of his tweet can be found in [docs](/docs/).

This program attempts to identify all such possible handles, and reports those
that exist, along with brief account stats. The scammers accounts share certain
traits: they have been created recently, have very few tweets, followers, and 
friends. Occasionally, they will have responded to some of the legit accounts. 

This tool can also be used to keep an eye on emerging typosquatters, frauds and 
brandjacking. This is useful as an additional source of targeted threat 
intelligence.

![Demo](/docs/tty.gif)

The idea is quite straightforward: *tweeptwist* takes in your Twitter username 
as a seed, generates a list of potential scam usernames and then checks to see
if they are registered. It also prints a set of relevant statistics for each
registered user it finds.

Attribution
------------
This program borrowes heavily from the excellent [*dnstwist*](https://github.com/elceef/dnstwist) 
written by *Marcin Ulikowski*.

You can reach the original author via:

- Twitter: [@elceef](https://twitter.com/elceef)
- LinkedIn: [Marcin Ulikowski](https://pl.linkedin.com/in/elceef)

Key features
------------

- Get key stats of a bunch of users in one go
- Obeys Twitter [guidelines](https://help.twitter.com/en/managing-your-account/twitter-username-rules) on username


Requirements
------------

You need to create a [Twitter app](https://apps.twitter.com/). Copy the *consumer_\** 
and *access_\** tokens for your app to [config.py](config.py) before you run the program. 

This program depends on the [*tweepy*](https://github.com/tweepy/tweepy) library to fetch usernames, and related
info. Installing tweepy is easy.

**Linux**

If you're on Linux, you can install tweepy like this:

```
$ sudo apt-get install tweepy
```

**OSX**

If you're on a Mac, you can install tweepy via
[Homebrew](https://github.com/Homebrew/homebrew) like so:

```
$ sudo easy_install tweepy
```

How to use
----------

The simplest way to run the tool is to specify a Twitter username as the only
argument. You can use `@example` or `example`. The program handles both versions.
The tool will run the fuzzing algorithm on `example` and generate a list of
potential usernames.
```
$ tweeptwist.py example
```
To obtain a sorted output, specify a column name of interest using the *--key*
argument. For example, to sort based on the number of tweets, use:
```
$ tweeptwist.py --key tweets example
```
The generated list of usernames outnumbers actually registered usernames. The
program, by default, shows only those which are registered. If you want to list
all possible usernames, you should use the *--all* argument.
```
$ tweeptwist.py --all example
```
**Note:** Sorting is not supported if you enable *--all*. The chosen key may not
be present for some of the generated variations (possibly because such an account
has not yet been registered).

CSV and JSON output formats are supported, so you can do:
```
$ tweeptwist.py --csv example > out.csv
$ tweeptwist.py --json example > out.json
```
It is fairly easy to use this tool to process multiple usernames:
```
for i in `sort influencers.txt`; do ./tweeptwist.py -q $i; done
```
If there are a lot of usernames, it helps to plan ahead. You can get a quick 
estimate of how many times the Twitter API will be called using the *--dry* option:
```
./tweeptwist.py -dq example
```
Note that the *--quiet* argument disables banner printing.

For a brief description of *tweeptwist* features, you can use:
```
$ tweeptwist.py --help
```

Issues
------
Given the rate-limit restrictions on the API, checking each username is time 
consuming.

The algorithm does not try to be aggresive: shorter usernames are not expanded
to the full 15 character limit.

The algorithm may list genuine, and even irrelevant usernames. The number of 
tweets; friend- and follower counts are some key parameters that can help 
distinguish scammers from genuine users.

Conversely, few or no tweets from a given username, or a low friend/follower
count does not necessarily mean that the account is not genuine.

Future work
-----------
1. Usernames generated by the fuzzing algorithms may not be sufficient. To
generate even more variants a dictionary file consisting of common username
prefixes and/or suffixes should be added. 
```
$ tweeptwist.py --dictionary dict.txt example
```

2. Support filtering for specific hashtags/keywords of interest in recent tweets 
of a given user. 
```
$ tweeptwist.py --tags BTC,wallet example
```
Alternatively, a small set of keywords/hastags found in the recent
N (say, 10) tweets should be printed along with account stats.

4. Feed the output to a ML engine?

References
-------

1. [Robert Wallhead](mailto:rwallhead@gmail.com) created an awesome Heroku 
version of *dnstwist*. Check out [*dnstwister*](https://dnstwister.report/). 

2. [URLCrazy](https://tools.kali.org/information-gathering/urlcrazy) is another 
excellent tool you should check out.

3. Artem Dinaburg wrote a great [article](http://dinaburg.org/bitsquatting.html)
on bit-squatting. For details, please see his Blackhat [whitepaper](http://media.blackhat.com/bh-us-11/Dinaburg/BH_US_11_Dinaburg_Bitsquatting_WP.pdf). 

Good luck!

Contact
-------

To send questions, comments or uggestions, just drop an e-mail at
[contact@banbreach.com](mailto:contact@banbreach.com)

You can also reach the author via:

- Twitter: [@Banbreach](https://twitter.com/Banbreach)
- LinkedIn: [Banbreach](https://in.linkedin.com/company/banbreach)

If you find the tool useful, let us know. You could also send some chocolates 
over to Marcin. Thank you.

