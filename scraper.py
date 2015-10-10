#!/usr/bin/env python3

"""
Script to get posts from reddit
"""

# Get data

import argparse, datetime, operator, praw, regex, sqlite3, sys, time
from submission_parser import SubmissionParser
import dateutil.parser

r = praw.Reddit(user_agent='reds')

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--subreddit', help="Subreddit to scrape")
parser.add_argument('-b', '--begin', help='Datetime (YYYY-MM-DD HH:MM:SS) of submissions to start scraping from')
parser.add_argument('-e', '--end', help='Datetime (YYYY-MM-DD HH:MM:SS) of submissions to end scraping at')
parser.add_argument('-l', '--limit', default=None, type=int, help='Number of posts to scrape')
# parser.add_argument('-s', '--skip', default=0, type=int, help='Number of posts to skip from start')
parser.add_argument('-t', '--test', default=False, action='store_true', help="If test flag included, don't update database")
parser.add_argument('--subs', help="Comma separated list of submission reddit_ids ('fullname' in reddit lingo) to scrape (setting this means datetime, limit and subreddit params are ignored")
args = parser.parse_args()

test = args.test

search_type = 'between_timestamps'

# If the --subs parameter is given, use this to decide which submissions to scrape, and ignore the datetime, limit and subreddit params
if args.subs:
  subsparam = args.subs.split(',')
  submissions = r.get_submissions(subsparam)
  num_posts = len(subsparam)
  print('Searching %s posts given in --subs parameter\n' % (num_posts))

else:
  if args.subreddit:
    subreddit = args.subreddit
  else:
    print('--subreddit/-s parameter is required')
    quit()
  num_posts = args.limit
  print('Num posts to scrape: ' + str(num_posts) + '\n')
  if args.test:
    print('Test run (posts will not be added to DB)')
  # Reddit API for some reason has timestamps offset by 8 hours. Need to correct this
  if args.begin:
    begin = str(time.mktime(dateutil.parser.parse(args.begin).timetuple()) + 28800).replace('.0', '')
  else:
    print('--begin/-b parameter is required')
    quit()
  if args.end:
    end = str(time.mktime(dateutil.parser.parse(args.end).timetuple()) + 28800).replace('.0', '')
  else:
    end = str(int(datetime.datetime.now().timestamp()) + 28800)
  query = 'timestamp:%s..%s' % (begin, end)
  print('Searching %s posts from %s from %s to %s\n' % (num_posts, subreddit, args.begin, args.end))
  print('search query will be %s\n' % (query))
  submissions = r.search(query, subreddit=subreddit, sort='new', limit = num_posts, syntax = 'cloudsearch')

con = sqlite3.connect('reds.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

if not test:
  res = cur.execute('insert into scrapes (datetime_started, subreddit, posts_to_search, posts_searched, posts_added, search_type) values (datetime(),?,?,?,?,?)', [subreddit, num_posts, 0, 0, search_type])
scrape_id = cur.lastrowid
con.commit()

cur.execute('select * from locations')
location_rows = cur.fetchall()

for i, submission in enumerate(submissions):
  print('submission ' + str(i+1) + ' of ' + str(num_posts) + '\n')
  if not test:
    cur.execute('update scrapes set posts_searched = posts_searched + 1 where scrape_id = ?', [scrape_id])
    con.commit()
  # Check to see if post has been downloaded previously and saved in DB, and if so skip it
  res = cur.execute('select id from scraped_posts where reddit_id = ?', [submission.fullname])
  if res.fetchone():
    print('%s: %s - created at %s - has already been added.\n' % (submission.fullname, submission.title, datetime.datetime.fromtimestamp(int(float(submission.created_utc)))))
    print('\n' + '*' * 70 + '\n')
    continue
  # Save post info in DB
  author_name = ''
  if submission.author:
    author_name = submission.author.name
  if not test:
    cur.execute('insert into scraped_posts (scrape_id, reddit_id, title, user, created, num_comments, score, content) values (?,?,?,?,?,?,?,?)', [scrape_id, submission.fullname, submission.title, author_name, submission.created_utc, submission.num_comments, submission.score, submission.selftext])
    cur.execute('update scrapes set posts_added = posts_added + 1 where scrape_id = ?', [scrape_id])
    con.commit()
  sp = SubmissionParser(submission.title)
  s = {}
  s['reddit_id'] = submission.fullname
  s['title'] = submission.title
  s['created'] = str(datetime.datetime.fromtimestamp(submission.created_utc))
  s['type'] = sp.match_type()

  matchlog = 'Matched type: %s.' % (s['type'])

  # Get age of poster
  s['poster_age'] = sp.match_age()

  matchlog = matchlog + ' Matched age: %s.' % (s['poster_age'])

  # Get whether success story
  s['success'] = 0
  if sp.match_success():
    s['success'] = 1

  matchlog = matchlog + ' Matched success: %s.' % (bool(s['success']))
  print(matchlog + '\n')

  # For logging
  print(s)
  if regex.search('[^\d\.]+', s['created']):
    s_created = s['created']
  else:
    s_created = datetime.datetime.fromtimestamp(int(float(s['created'])))
  print('%s: %s - created at %s\n' % (s['reddit_id'], s['title'], s_created))

  sp.match_location()
  chosen_location_id = sp.chosen_location['location_id'] if sp.chosen_location else None
  if not test:
    cur.execute('update scraped_posts set location_id = ?, type = ?, poster_age = ?, success = ? where reddit_id = ?', [chosen_location_id, s['type'], s['poster_age'], s['success'], s['reddit_id']])
    if chosen_location_id:
      matchnum_str = 'Updating locations table.'
      print(matchnum_str + '\n')
      cur.execute('update locations set has_matched = 1 where location_id = ?', [chosen_location_id])
    con.commit()
  print('\n' + '*' * 70 + '\n')
