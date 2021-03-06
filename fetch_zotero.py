#!/usr/bin/env python3

import os
import sys
import re
from pyzotero import zotero
import pyaml

def fetch_zotero(api_key, library_id, collection_id, pubdir, lab_publication):

    def get_zotero_collection(zot_api, collection_id):
        """Get elements from a zotero collection."""
        items = zot_api.everything(zot_api.collection_items(collection_id))
        return [item['data'] for item in items
                if item['data']['itemType'] != 'attachment'
                and 'parentItem' not in item['data']]

    def format_date(date):
        """Returns the year from a date string."""
        for separator in [' ', '-', '/', ',']:
            date = date.replace(separator, '_')
        date = date.split('_')
        for d in date:
            if len(d) == 4 and d.isnumeric():
                return d

    def format_doi(doi):
        """Returns a simplified DOI string."""
        to_delete = ['http://dx.doi.org/', 'dx.doi.org/']
        for phrase in to_delete:
            doi = doi.replace(phrase, '')
        return doi

    def format_firstname(firstname):
        """Abbreviates firstname if necessary."""
        separated = firstname.split(' ')
        separated = [name.split('-') for name in separated]
        separated = [item for sublist in separated for item in sublist]
        if len(separated) == 1:
            return firstname[0] + '.'
        else:
            return '.'.join([name[0] for name in separated if name]) + '.'

    def format_authorship(creators):
        """Returns a formatted full authorship string."""
        authors = []
        for creator in creators:
            if creator['creatorType'] == 'author' and 'lastName' in creator and 'firstName' in creator:
                if 'firstName' in creator:
                    firstname = format_firstname(creator['firstName'])
                else:
                    firstname = ''
                lastname = creator['lastName']
                authors += [firstname + ' ' + lastname]
            elif creator['creatorType'] == 'author' and 'name' in creator:
                authors += [creator['name']]
        return authors

    def create_filename(article):
        """Returns a string that can be used as a unique filename."""
        if 'lastnames' in articles:
            author = article['lastnames'][0]
        else:
            author = article['authorship'][0].split(' ')[0]
        author = re.sub('[^a-zA-Z0-9-_*.]', '', author)
        year = article['year']
        title = article['title'].title()
        title = re.sub('[^a-zA-Z0-9-_*.]', '', title)
        if not year:
            year = "0000"
        if not title:
            title = "XXXX"
        if not author:
            author = "XX"
        return author + year + '_' + title[0:25]

    zot = zotero.Zotero(
        library_id=library_id,
        library_type="group",
        api_key=api_key
    )

    articles = get_zotero_collection(zot, collection_id)

    collection = []
    for article in articles:
        data = {}
        data['doi'] = format_doi(article['DOI'])
        data['journal'] = article['publicationTitle']
        data['title'] = article['title']
        data['pubURL'] = article['url']
        data['issue'] = article['issue']
        data['volume'] = article['volume']
        data['year'] = format_date(article['date'])
        data['keyword'] = [tag['tag'] for tag in article['tags']]
        data['lastnames'] = [creator['lastName'] for creator in article['creators']
                             if 'lastName' in creator]
        data['authorship'] = format_authorship(article['creators'])
        data['itemType'] = article['itemType']
        data['labPublication'] = lab_publication
        collection += [data]

    for article in collection:
        filename = create_filename(article) + '.md'
        filepath = os.path.join(pubdir, filename)
        yamlblock = pyaml.dump(article)
        with open(filepath, 'w') as md:
            md.write('---\n')
            md.write(yamlblock)
            md.write('---')
