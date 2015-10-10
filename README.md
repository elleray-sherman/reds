[RAOX stats](http://elleray-sherman.github.io/)

Reddit data scraping
=====================

- Python scripts access the [reddit API](https://www.reddit.com/dev/api) using [PRAW](https://praw.readthedocs.org/en/stable/)
- They parse the submissions for the selected subreddit for post type, location etc. information
- For location matching, a table of global cities, regions, and countries is used. Table is a modifed version of Maxmind's [Free World Cities Database](https://www.maxmind.com/en/free-world-cities-database).

Usage
-------

- To run a scrape for 10 posts in the day following January 1st 2015, run:

```bash
./scraper.py --subreddit randomactsofblowjob --begin '2015-1-1 00:00' --end '2015-1-2 00:00' --limit 10
```

To update locations for posts with missing locations already in the database, run:

```bash
./updater.py --do missing_locations
```

- To see all options for scraper.py and updater.py, run them with the flag `--help`

Data presentation statistics
==========================

Data presentation HTML files created with Knitr and R Markdown, interfacing with database populated from reddit scraping scripts and world locations list.

Database
========

Contains tables for scrape and scraped post information, together with table of locations to match against. The version in this repository does not contain scraped post data from running the scripts, but does contain the full locations table.

Location types are as follows:

- 1 = City
- 2 = Region
- 3 = Country
- 4 = Metropolitan areas (unused)
- 5 = Neighbourhood (unused)
- 6 = 'Small region' (similar to a metropolitan area)
