'''
utils
'''

import sys
from json import load
from time import localtime
from random import getrandbits


class DBBase:
    '''
    This class is inherited by the main Database class. It provides
    the Database class with board & MicroPython specific properties.
    '''
    def __init__(self):
        self.config = load_config()
        self.board = sys.platform
        self.python_version = sys.version
        self.mp_version = '.'.join(
            [str(i) for i in sys.implementation.version]
        )
        self.device_id = self.config['device_id']
        self.utc_offset = self.config['utc_offset']
        self.cleanup_seconds = self.config['cleanup_seconds']


class Document:
    '''
    Class for taking in a database document(dict) and setting
    class attributes for nested objects with '__' delimeter for filter
    functionality.
    '''
    def __init__(self, document):
        self._set_attrs(document)

    def __getitem__(self, attr):
        return getattr(self, attr)

    def _set_attrs(self, dct, parent=None):
        for key, value in dct.items():
            if isinstance(value, dict) and not parent:
                self._set_attrs(value, parent=key)
            elif isinstance(value, dict):
                key = '__'.join((parent, key),)
                self._set_attrs(value, parent=key)
            elif parent:
                key = '__'.join((parent, key),)
                setattr(self, key, value)
            else:
                if isinstance(value, list):
                    setattr(self, key, str(value))
                else:
                    setattr(self, key, value)


def load_config() -> dict:
    '''
    This function loads configuration file located in TetherDB/config.json
    to set main Database class properties.
    '''
    with open('TetherDB/config.json') as config_file:
        config = load(config_file)
    if not config['device_id']:
        config['device_id'] = '{}-device'.format(sys.platform)
    try:
        config['cleanup_seconds'] = int(config['cleanup_seconds'])
    except ValueError:
        config['cleanup_seconds'] = ''

    return config


def load_db(db_filepath: str, write_mode: str = '') -> any:
    '''
    This function either loads or overwrites a database file depending
    on need and access permissions.
    '''
    if write_mode in ('rb', 'r+b', 'w+b'):
        return open(db_filepath, write_mode)

    db_file = open(db_filepath, write_mode)
    db_file.close()

    return None


def generate_id(db_object: any) -> str:
    '''
    This function generates a random id for Database documents.
    Checks if key exists in btree database, if not returns to write.
    '''
    while True:
        doc_id = str(getrandbits(24))
        if doc_id in db_object.keys():
            generate_id(db_object)
            break

        return doc_id


def add_id(document_id: int, document: dict) -> dict:
    '''
    This function simple adds the key from btree record
    and adds it to document as 'doc_id' for generator comprehension
    called in read(query_all=True)
    '''
    document['document_id'] = document_id

    return document


def iso_time(timestamp: int,
             utc_offset: str = '+00:00') -> str:
    '''
    This function formats timestamp for ISO8601 time formate from timestamp
    provided. Optionally takes in a utc_offset(str). Defaults to '+00:00'
    '''
    time_format = list(localtime(timestamp))[0:6]
    for index, date_item in enumerate(time_format):
        if date_item < 10:
            time_format[index] = ''.join(('0', str(date_item)))

    return '{}-{}-{}T{}:{}:{}{}'.format(time_format[0], time_format[1],
                                        time_format[2], time_format[3],
                                        time_format[4], time_format[5],
                                        utc_offset)


def time_to_iso(document: dict, utc_offset: str = '') -> dict:
    '''
    This function is used to inject ISO8601 timestamp into document for read.
    Time is saved in databse as seconds since MicroPython epoch.
    '''
    if utc_offset:
        document['timestamp'] = iso_time(document['timestamp'],
                                         utc_offset=utc_offset)
    else:
        document['timestamp'] = iso_time(document['timestamp'])
    return document


def tether(db_filepath: str = '', device_id: bool = True):
    '''
    Decorator that takes in a function that returns dict and writes to
    database. Optiionally can specify db_filepath and enable/disable
    device_id in document.
    '''
    def wrapper(func):
        def wrapped_function(*args, **kwargs):
            from .db import Database

            if not db_filepath:
                database = Database()
            else:
                database = Database(db_filepath)

            data = func(*args, **kwargs)

            if not device_id:
                database.write(data, device_id=False)
            else:
                database.write(data)

        return wrapped_function
    return wrapper
