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
    Database class
    '''
    def __init__(self, db_filepath: str = 'TetherDB/Tether.db') -> None:
        super().__init__()
        self.db_filepath = db_filepath
        self.db = self._db_init()
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

    def __getitem__(self, doc_id):
        return self.read(doc_id)

    def __delitem__(self, doc_id):
        return self.delete(doc_id)

    def _db_init(self):
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
        Takes in dict event and write document to db filepath.
        '''
        if not isinstance(document, dict):
            raise TypeError("Invalid type. Document must be of type 'dict'.")

        doc_id = generate_id(self.db)
        document.update(timestamp=time())
        if device_id:
            document.update(device_id=self.device_id)

        self.db.put(doc_id, dumps(document).encode())
        self.db_len += 1
        self.db.flush()
        sleep(0.01)

    def delete(self, doc_id: str = '', drop_all: bool = False) -> str:
        '''
        Deletes a single document with doc_id(int). drop_all param(boolean) drops all documents.
        Returns str of how many documents deleted.
        '''
        if doc_id and not drop_all:
            try:
                del self.db[doc_id]
                self.db.flush()
                self.db_len -= 1
                documents_deleted = 1
            except KeyError:
                return 'doc_id not found'

        elif drop_all and not doc_id:
            documents_deleted = self.db_len
            self.db_len = 0
            self.db.close()
            load_db(self.db_filepath, write_mode='wb')
            self.db = btree.open(load_db(self.db_filepath, 'r+b'), pagesize=1024)

        return '{} documents deleted'.format(documents_deleted)

    def read(self, document_id: str = '', iso_8601: bool = True,
             query_all: bool = False) -> any:
        '''
        Can retrieve single record with document_id(str). Can also query
        all records withquery_all(bool).
        '''
        results = None

        if document_id and not query_all:
            for doc_id, document in self.db.items():
                if document_id == doc_id.decode():
                    if iso_8601:
                        if self.utc_offset:
                            document = time_to_iso(loads(document), self.utc_offset)
                        else:
                            document = time_to_iso(loads(document))
                    document['id'] = doc_id.decode()
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
            print('Provide document_id or query_all=True')

        if not results:
            return 'No documents found matching document_id'

        return results

    def filter(self, **kwargs) -> any:
        '''
        Filter takes in key value pairs to search via an 'AND' expression. It will return
        documents containing all matching key and values. Also accepts trailing wilcards for values.
        '''
        query_set = []

        def _queryset_append(document: dict, db_doc: dict) -> None:
            if document not in query_set:
                query_set.append(db_doc)


        def _wildcard_query(document: dict, key: str, value: any) -> None:
            pattern = re.compile(r'{}'.format(value[:-1]))
            if pattern.match(str(document[key])):
                return True
            return False


        def _frozen_compare(keywords: dict, document: dict, db_doc: dict) -> bool:
            if (frozenset(keywords.items()) & frozenset(document.items())
                    == set(keywords.items())):
                _queryset_append(document, db_doc)
                return True
            return False

        for doc_id, db_doc in (doc for doc in self.db.items()):
            if self.utc_offset:
                db_doc = time_to_iso(add_id(doc_id, loads(db_doc)), self.utc_offset)
            else:
                db_doc = time_to_iso(add_id(doc_id, loads(db_doc)))

            document_class = Document(db_doc)
            matched_kwargs = {}

            if _frozen_compare(kwargs, document_class.__dict__, db_doc):
                continue
            for key, value in kwargs.items():
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
        Purges database documents based on integer passed in either seconds
        parameter or setting Database.cleanup_seconds.
        '''
        if self.cleanup_seconds:
            seconds = self.cleanup_seconds
        elif seconds and not isinstance(seconds, int):
            raise TypeError("Invalid type. seconds must be of type 'int'.")
        elif not seconds:
            return "Please provide seconds: int or set Database." \
                "cleanup_seconds attribute with integer."

        documents_deleted = 0

        for doc_id, document in self.db.items():
            if time() - loads(document)['timestamp'] >= seconds:
                del self.db[doc_id]
                self.db_len -= 1
                documents_deleted += 1

        self.db.flush()

        return '{} documents deleted'.format(documents_deleted)
