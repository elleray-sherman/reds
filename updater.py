#!/usr/bin/env python3

"""
Script to go over existing posts that have been saved, and check / update their information.
"""

import argparse, datetime, operator, praw, regex, sqlite3, sys
from submission_parser import SubmissionParser

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--do', choices=['all_locations', 'missing_locations','ages'], required=True, help='Update action to take')
parser.add_argument('-l', '--limit', default=None, type=int, help='Number of posts to update')
parser.add_argument('-s', '--skip', default=0, type=int, help='Number of posts to skip')
parser.add_argument('-t', '--test', default=False, action='store_true', help="If test flag included, don't update database")
parser.add_argument('--subs', help="Comma separated list of submission reddit_ids ('fullname' in reddit lingo) to scrape (setting this means datetime, limit and subreddit params are ignored")
args = parser.parse_args()

get_reddit_data = False
scrape_title_data = False
update_all_locations = False
update_missing_locations = False
update_ages = False

if args.do == 'all_locations':
  update_all_locations = True
if args.do == 'missing_locations':
  update_missing_locations = True
if args.do == 'ages':
  update_ages = True

subs_to_update = None
if args.subs:
  subs_to_update = args.subs.split(',')

limit = None
if args.limit:
  limit = args.limit

skip = 0
if args.skip:
  skip = args.skip

test = False
if args.test == True:
  test = True

con = sqlite3.connect('reds.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

last_modified_datetime = str(datetime.datetime.utcnow())

# if get_reddit_data:
#   r = praw.Reddit('reds')
#   cur.execute('select reddit_id from scraped_posts')
#   cur2 = con.cursor()
#   while True:
#     reddit_ids_tuples = cur.fetchmany(100)
#     print(reddit_ids_tuples)
#     if not reddit_ids_tuples:
#       break
#     reddit_ids = [i[0] for i in reddit_ids_tuples]
#     # Get info from reddit
#     subs = r.get_submissions(reddit_ids)
#     for i, sub in enumerate(subs):
#       print('loopcount: %s' % (i))
#       s = sub
#       author_name = ''
#       print(s.fullname)
#       if s.author:
#         author_name = s.author.name
#         print(s.author.name)
#         print(type(s.author.name))
#       print(s.num_comments)
#       print(s.score)
#       print(s.selftext)
#       print(s.created_utc)
#       print('*' * 50)
#       cur2.execute('update scraped_posts set user = ?, num_comments = ?, score = ?, content = ?, created = ? where reddit_id = ?', [author_name, s.num_comments, s.score, s.selftext, s.created_utc, s.fullname])
      
#     con.commit()
#     print(reddit_ids_tuples)

if update_all_locations or update_missing_locations or update_ages:
  stmt = 'select * from scraped_posts'
  log = 'Updating'
  if update_all_locations or update_missing_locations:
    log = log + ' locations'
  if update_ages:
    log = log + ' ages'
  log = log + ' of posts in scraped_posts'
  if update_missing_locations:
    stmt = stmt + ' where location_id is null'
    log = log + ' which have a null location currently'
  elif subs_to_update:
    stmt = stmt + " where reddit_id in('" + "','".join(subs_to_update) + "')"
    log = log + ' in the list ' + ','.join(subs_to_update)
  if limit:
    stmt = stmt + ' limit ' + str(limit)
    log = log + ' (limit to %s' % limit + ' posts)'
  if skip:
    log = log + ' (skip %s' % skip + ' posts)'
  if test:
    log = log + ' (test run)'

  print(stmt)

  cur.execute(stmt)
  subs = cur.fetchall()
  log = log + ':\n'
  print(log)
  print('\n' + '*' * 70 + '\n')
  for i,s in enumerate(subs[skip:]):
    print('Submission ' + str(i+skip+1) + ' of ' + str(limit) + '\n')
    print('%s: %s - created at %s. Last updated at %s\n' % (s['reddit_id'], s['title'], datetime.datetime.fromtimestamp(int(float(s['created']))), s['last_modified']))
    sp = SubmissionParser(s['title'])
    if update_all_locations or update_missing_locations:
      sp.match_location()
      chosen_location_id = sp.chosen_location['location_id'] if sp.chosen_location else None
      if not test:
        print('Updating scraped_posts with new location\n')
        cur.execute('update scraped_posts set location_id = ?, last_modified = ? where reddit_id = ?', [chosen_location_id, last_modified_datetime, s['reddit_id']])
        print('Updating has_matched for location\n')
        cur.execute('update locations set has_matched = 1 where location_id = ?', [chosen_location_id])
        con.commit()
    if update_ages:
      chosen_age = sp.match_age()
      if not test:
        print('Updating scraped posts with matched age.\n')
        cur.execute('update scraped_posts set poster_age = ?, last_modified = ? where reddit_id = ?', [chosen_age, last_modified_datetime, s['reddit_id']])
        con.commit()
    print('\n' + '*' * 70 + '\n')


