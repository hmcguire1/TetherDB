'''
Database module for TetherDB
'''
import re
from os import listdir
from json import loads, dumps
from time import time, sleep

import btree
from .utils import (DBBase, Document, load_db, generate_id, add_id,
                    time_to_iso)


class Database(DBBase):
    '''
    The Database class is the main entrypoint for working with local database.
    The path defaults to TetherDB/Tether.db with no arumunets passed.
    It inherits from DBBase which provides board specific properties.
    Optionally takes a str as the sole argument to the path where the db
    file will be stored. If the specified file does not exist it creates it.
    If file is not located in root directory, parent dirs must already exist.
    '''
    def __init__(self, db_filepath: str = 'TetherDB/Tether.db') -> None:
        super().__init__()
        self.db_filepath = db_filepath
        self.db = self._db_init()
        if self.db:
            self.db_len = len([doc for doc in self.db.keys()])

    def __repr__(self) -> str:
        return 'Database -> {}'.format(self.db_filepath)

    def __str__(self):
        return 'Database(db_filepath={}, db_len={}, utc_offset={}, cleanup_seconds={})'.format(
            self.db_filepath, self.db_len,
            self.utc_offset if self.utc_offset else None,
            self.cleanup_seconds if self.cleanup_seconds else None)

    def __len__(self):
        return self.db_len

    def __getitem__(self, _id):
        return self.read(_id)

    def __delitem__(self, _id):
        return self.delete(_id)

    def _db_init(self):
        '''
        This function intitializes the database file. If the specified
        database file does not exist it creates it. If file is not located
        in root directory, parent directories must already exist.
        '''
        try:
            if (self.db_filepath.split('/')[-1] not in
                    listdir('/'.join([file for file in self.db_filepath.split('/')[0:-1]]))):
                return btree.open(load_db(self.db_filepath, write_mode='w+b'),
                                  pagesize=1024)
            return btree.open(load_db(self.db_filepath, write_mode='r+b'),
                              pagesize=1024)

        except OSError:
            print('Please create db_filepath parent directories')
            return None

    def write(self, document: dict, device_id: bool = True) -> None:
        '''
        This Method takes in a dict to write a document to db_filepath.
        The device_id argument allows adding a device id to documents.
        This is True by default, if not set in config file it will be set
        to '{sys.platform}-device'.
        '''
        if not isinstance(document, dict):
            raise TypeError("Invalid type. Document must be of type 'dict'.")

        _id = generate_id(self.db)
        document.update(timestamp=time())

        if device_id:
            document.update(device_id=self.device_id)

        self.db.put(_id, dumps(document).encode())
        self.db_len += 1
        self.db.flush()
        sleep(0.01)

    def delete(self, _id: str = '', drop_all: bool = False) -> str:
        '''
        This method can delete a single document with _id(int) param or can
        delete all documents in database with drop_all(bool) param.
        Returns str of how many documents deleted.
        '''
        if _id and not drop_all:
            try:
                del self.db[_id]
                self.db.flush()
                self.db_len -= 1
                documents_deleted = 1
            except KeyError:
                return '_id not found'

        elif drop_all and not _id:
            documents_deleted = self.db_len
            self.db_len = 0
            self.db.close()
            load_db(self.db_filepath, write_mode='wb')
            self.db = btree.open(load_db(self.db_filepath, 'r+b'), pagesize=1024)

        return '{} documents deleted'.format(documents_deleted)

    def read(self, document_id: str = '', iso_8601: bool = True,
             query_all: bool = False) -> any:
        '''
        This method can either retrieve single document with document_id(str) param or
        can also query all documents in database with query_all(bool) param.
        query_all returns a generator or None if 0 records in database.
        '''
        results = None

        if document_id and not query_all:
            for doc_id, document in self.db.items():
                db_doc = loads(document)

                if document_id == doc_id.decode():
                    if iso_8601:
                        if self.utc_offset:
                            document = time_to_iso(db_doc, self.utc_offset)
                        else:
                            document = time_to_iso(db_doc)
                    document['_id'] = doc_id.decode()
                    results = document
        elif query_all and not document_id:
            if iso_8601:
                if self.utc_offset:
                    results = (
                        time_to_iso(add_id(doc_id, loads(document)))
                        for doc_id, document in self.db.items()
                    )
                else:
                    results = (
                        time_to_iso(add_id(doc_id, loads(document)), self.utc_offset)
                        for doc_id, document in self.db.items()
                    )
            else:
                results = (
                    add_id(doc_id, loads(document))
                    for doc_id, document in self.db.items()
                )
        else:
            print('Provide _id or query_all=True')

        return results

    def filter(self, **kwargs) -> any:
        '''
        This method takes in key, value to search via an 'AND' expression.
        It will return documents containing all matching key sand values. To
        search nested objects use the '__' delimeter. Such as 'name__first'

        Values can also be trailing wilcards within quotes.
        '''
        query_set = []

        def _queryset_append(db_doc: dict) -> None:
            if db_doc not in query_set:
                query_set.append(db_doc)


        def _wildcard_query(document: dict, key: str, value: any) -> None:
            pattern = re.compile(r'{}'.format(value[:-1]))
            if pattern.match(str(document[key])):
                return True
            return False


        def _frozen_compare(keywords: dict, document: dict, db_doc: dict) -> bool:
            if (frozenset(keywords.items()) & frozenset(document.items())
                    == set(keywords.items())):
                _queryset_append(db_doc)
                return True
            return False

        for _id, db_doc in (doc for doc in self.db.items()):
            if self.utc_offset:
                db_doc = time_to_iso(add_id(_id, loads(db_doc)), self.utc_offset)
            else:
                db_doc = time_to_iso(add_id(_id, loads(db_doc)))

            document_class = Document(db_doc)
            matched_kwargs = {}
            kw_items = {}

            for key, value in kwargs.items():
                if isinstance(value, list):
                    kw_items[key] = str(value)
                else:
                    kw_items[key] = value
                if _frozen_compare(kw_items, document_class.__dict__, db_doc):
                    continue

            for key, value in kw_items.items():
                if str(value).endswith('*'):
                    match = _wildcard_query(document_class.__dict__, key=key, value=value)
                    if match:
                        matched_kwargs[key] = document_class.__dict__[key]
            if matched_kwargs:
                _frozen_compare(matched_kwargs, document_class.__dict__, db_doc)

        return ((document for document in query_set) if len(query_set) >= 1
                else None)

    def cleanup(self, seconds: int = None) -> str:
        '''
        This method purges database documents based on integer
        passed in either seconds parameter or setting Database.cleanup_seconds.
        Will delete records where timestamp is >= seconds passed from time method
        is called.
        '''
        if self.cleanup_seconds:
            seconds = self.cleanup_seconds
        elif seconds and not isinstance(seconds, int):
            raise TypeError("Invalid type. seconds must be of type 'int'.")
        elif not seconds:
            return "Please provide seconds: int or set Database." \
                "cleanup_seconds attribute with integer."

        documents_deleted = 0

        for _id, document in self.db.items():
            if time() - loads(document)['timestamp'] >= seconds:
                del self.db[_id]
                self.db_len -= 1
                documents_deleted += 1

        self.db.flush()

        return '{} documents deleted'.format(documents_deleted)
