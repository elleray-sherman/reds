import datetime,operator,regex,sqlite3

class SubmissionParser(object):

  con = sqlite3.connect('reds.db')
  con.row_factory = sqlite3.Row
  cur3 = con.cursor()
  cur3.execute('select * from locations where type in (1,6) and location_id not in (select * from view_false_match_cities) and location_id not in (select * from view_false_match_city_ids) order by has_matched desc')
  city_rows = cur3.fetchall()

  city_rows_prev_matched = list(filter(lambda row: row if row['has_matched'] > 0 else False, city_rows))
  city_rows_unmatched = list(filter(lambda row: row if row['has_matched'] == 0 else False, city_rows))

  cur3.execute('select * from locations where type = 2 order by has_matched desc')
  region_rows = cur3.fetchall()

  cur3.execute('select * from locations where type = 3 order by has_matched desc')
  country_rows = cur3.fetchall()

  false_match_regions = ['AS','HI','IN','ME','OK','OR']

  def __init__(self, title):
    self.title = title
    self.chosen_location = None
    self.allowed_sub_types = ['m4f','m4m','f4m','mf4m','mf4f','m4mf','f4mf','f4f','m4a','f4a','m4t','t4m']
    self._matched_cities = []
    self._matched_regions = []
    self._matched_countries = []
    self._filtered_matched_cities = None
    self._chosen_city = None
    self._chosen_region = None
    self._chosen_country = None
    self._matched_age = None
    self._matched_success = None

  def match_type(self):
    sub_type_match = regex.search('[mf]*[mfta]4[mfta][mf]*', self.title, regex.I)
    if sub_type_match:
      sub_type = sub_type_match.group(0).lower()
      # If type is like fm4f change it to be like mf4f for consistency
      if sub_type.split('4')[0] == 'fm': sub_type = 'mf4' + sub_type.split('4')[1]
      if sub_type.split('4')[1] == 'fm': sub_type = sub_type.split('4')[0] + '4mf'

      if sub_type not in self.allowed_sub_types:
        sub_type = None

      return sub_type

  def match_age(self):
    print('Checking title for age match.')
    # Many subs add y after age e.g. 25y or 22yo
    age_match = regex.search(r'\b(\d{2})(yo?)?\b', self.title)
    if age_match and age_match.group(1) != '69':
      log = 'Age match found: %s\n' % (age_match.group(0))
      if age_match.group(0) != age_match.group(1):
        log = log + 'Chosen age: %s\n' % (age_match.group(1))
      print(log)
      self._matched_age = age_match.group(1)
      return self._matched_age

  def match_success(self):
    if regex.search('\[[\]]*success[\]]*\]', self.title, regex.I):
      self._matched_success = True
      return True

  def _choose_city(self):
    # If we have multiple cities in self._matched_cities, we need to choose one of them. We first check to see if there are any clues to the city's location in the submission title, and after this filter has been applied choose the remaining city with the largest population
    if not self._matched_cities:
      return
    # See if there are any clues in the submission title as to the region or country the city is in
    for row in self.region_rows:
      # For US states only check the code (uppercase)
      if row['region'] and row['country'] == 'us':
        if regex.search(r'\b%s\b' % row['region'], self.title):
          self._chosen_region = row
          break
      # For all regions check the region name and alt names
      region_names = row['region_name'] if not row['alt_names'] else row['region_name'] + '|' + row['alt_names'].replace(',', '|')
      if regex.search(r'\b%s\b' % region_names, self.title, regex.I):
        self._chosen_region = row
        break

    # If no matching region found check country
    if self._chosen_region is None:
      for row in self.country_rows:
        # Add alt names if they exist
        country_names = row['country_name'] if not row['alt_names'] else row['country_name'] + '|' + row['alt_names'].replace(',', '|')
        if regex.search(r'\b%s\b' % country_names, self.title, regex.I):
          self._chosen_country = row
          break

    # If submission title has a matching city AND a matching region/country, restrict matching locations to the ones that match both
    if self._chosen_region:
      self._filtered_matched_cities = list(filter(lambda city: city if city['region'] == self._chosen_region['region'] or city['region_name'] == self._chosen_region['region_name'] else False, self._matched_cities))
    elif self._chosen_country:
      self._filtered_matched_cities = list(filter(lambda city: city if city['country'] == self._chosen_country['country'] else False, self._matched_cities))

    # Of the remaining choices, select the one with the largest population
    if self._filtered_matched_cities:
      self._chosen_city = sorted(self._filtered_matched_cities, key=operator.itemgetter('population'), reverse=True)[0]
    else:
      self._chosen_city = sorted(self._matched_cities, key=operator.itemgetter('population'), reverse=True)[0]


  def _match_cities(self,prev_matched=False):

    rows = self.city_rows_prev_matched if prev_matched else self.city_rows_unmatched

    for row in rows:
      # Contruct regex matching pattern, matching for city name and alt names in title with and without spaces
      pattern = r'\b(north|northern|south|southern|east|eastern|west|western|central|downtown|suburbs|burbs)?(' + row['city'].replace(' ','\s?')
      if row['alt_names']:
        pattern = pattern + '|' + row['alt_names'].replace('.', '\.').replace(' ','\s?').replace(',','|')

      # If title contains city state concat, add matching for US states concatenated with city name
      if row['country'] == 'us':
        pattern = pattern + '(' + row['region'] + ')?'

      pattern = pattern + r')\b'

      # If a matching city name is found in submission title, add it to the list (check for city in title with and without spaces)
      if regex.search(pattern, self.title, regex.I):
        self._matched_cities.append(dict(row))
        print('Regex pattern matched: %s' % (pattern))

    print('\nMatched cities:')
    print(self._matched_cities)
    print('')

  def _match_region(self):
    for row in self.region_rows:
      # Contruct regex matching pattern, matching for region name and alt names in title with and without spaces
      # Some posts have compass direction before region, e.g. northernvirginia. Check for these before region name
      pattern = r'\b(north|northern|south|southern|east|eastern|west|western|central|upstate)?(' + row['region_name'].replace(' ','\s?')
      if row['alt_names']:
        pattern = pattern + '|' + row['alt_names'].replace('.', '\.').replace(' ','\s?').replace(',','|')
      # Add the region acronym, eg for US states. Exclude those that match common words, e.g. ME, IN
      if row['region'] and row['region'] not in self.false_match_regions:
        pattern = pattern + '|' + row['region']
      pattern = pattern + r')\b'
      if regex.search(pattern, self.title, regex.I):
        print('Regex pattern matched: %s' % (pattern))
        self._matched_regions.append(dict(row))
        print('Matched region:')
        print(self._matched_regions)
        print('')
        self._chosen_region = self._matched_regions[0]
        break

  def _match_country(self):
    for row in self.country_rows:
      # Contruct regex matching pattern, matching for country name and alt names in title with and without spaces
      # Some posts have compass direction before country, e.g. northwales. Check for these before country name
      pattern = r'\b(north|northern|south|southern|east|eastern|west|western|central)?(' + row['country_name'].replace(' ','\s?')
      if row['alt_names']:
        pattern = pattern + '|' + row['alt_names'].replace('.', '\.').replace(' ','\s?').replace(',','|')
      pattern = pattern + r')\b'
      if regex.search(pattern, self.title, regex.I):
        print('Regex pattern matched: %s' % (pattern))
        self._matched_countries.append(dict(row))
        print('Matched country:')
        print(self._matched_countries)
        print('')
        self._chosen_country = self._matched_countries[0]
        break

  def match_location(self):
    # Most submissions will match a small number of popular locations (e.g. New York, Los Angeles etc.). To save the script searching through all world cities every time, try locations that have already matched first, and if a post matches one of these with no indications it should match something different instead, match with this post and don't search through any more.
    print('Checking previously matched cities\n')
    self._match_cities(True)
    # If a previously selected city has matched, check the title for any region or country info that contradicts the selection of the previously matched city. If it does match then it's like the correct match is a different city, so we need to search through all the cities
    if self._matched_cities:
      # If only one city has matched, choose that one
      if len(self._matched_cities) == 1:
        self._chosen_city = self._matched_cities[0]
        self.chosen_location = self._chosen_city
      else:
        self._choose_city()
        self.chosen_location = self._chosen_city
      self._match_region()
      self._match_country()
      if self._chosen_region and self._chosen_region['region'] != self._chosen_city['region']:
          self.chosen_location = None
      print(self._chosen_city)
      print(self._chosen_country)
      if self._chosen_country and self._chosen_country['country'] != self._chosen_city['country']:
          self.chosen_location = None

    if not self.chosen_location:
      print('No match found in previously matched cities. Checking unmatched cities\n')
      # If no match for previous city matches, search the full list
      self._match_cities(False)
      # If there are matching cities, select which one to choose
      if self._matched_cities:
        # If only one city has matched, choose that one
        if len(self._matched_cities) == 1:
          self.chosen_location = self._matched_cities[0]
        else:
          self._choose_city()
          self.chosen_location = self._chosen_city

    # If no city has been matched try matching with region
    if not self.chosen_location:
      if not self._chosen_region:
        print('No match found. Checking regions.\n')
        self._match_region()
        if self._chosen_region:
          self.chosen_location = self._chosen_region

    # If no city or region has been matched try matching with country
    if not self.chosen_location:
      if not self._chosen_country:
        print('No match found. Checking countries.\n')
        self._match_country()
        if self._chosen_country:
          self.chosen_location = self._chosen_country

    if self.chosen_location and self.chosen_location['location_id']:
      print('Chosen location: %s, %s/%s, %s/%s\n' % (self.chosen_location['city'],self.chosen_location['region'],self.chosen_location['region_name'],self.chosen_location['country'],self.chosen_location['country_name']))
      print(self.chosen_location)
      print('')
