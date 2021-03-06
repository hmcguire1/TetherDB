# TetherDB
### Simplistic document database for MicroPython.
*A pure python library written for resource-limited microcontrollers such as ESP8266 & ESP32.*
<br>

> Features:
- Simple syntax
- Works natively with MicroPython. Tested with v1.12, v1.13, v1.14
- Easily integrates into existing projects
- Maintain multiple databases on a single device
- Write and query nested objects

Installation
---
- Requires a library such as rshell to copy directory onto device
[rshell - GitHub](https://github.com/dhylands/rshell)

```sh
git clone https://github.com/hmcguire1/TetherDB.git
cd TetherDB
rshell -p /dev/ttyUSB0
rsync TetherDB /pyboard/TetherDB
```
Configuration
---
*Configuration filepath: TetherDB/config.json*
- device_id(str): Add a custom device_id attribute to documents. Defaults to {sys.platform}-device
- utc_offset(str): Add utc_offset to timestamp (&#177;dd:dd). Defaults to '+00:00'
- cleanup_seconds(int): Add an integer to call cleanup function with no arguments.

Database
---

&nbsp;&nbsp;*Database(db_filepath: str = 'TetherDB/Tether.db') - > None*

```python
from TetherDB import Database
new_db_1 = Database() #Default filepath of ('TetherDB/Tether.db')
new_db_2 = Database('test.db') #root dir
new_db_3 = Database('TestDir/other_test.db') #parent dirs must exist prior to database file creation

str(new_db_1)
>>> 'Database(db_filepath=TetherDB/Tether.db, db_len=0, utc_offset=None, cleanup_seconds=None)'

str(new_db_2)
>>> 'Database(db_filepath=test.db, db_len=0, utc_offset=None, cleanup_seconds=None)'

str(new_db_3)
>>> 'Database(db_filepath=TestDir/other_test.db, db_len=0, utc_offset=None, cleanup_seconds=None)'
```

Database Methods
---

> **Write:**

&nbsp;&nbsp;*write(document: dict, device_id: bool = True) → None*

- Two methods of writing:
    - Instantiating a database object
    - Tether decorator
- Accepts a Dict type for document
- device_id accepts bool type for injecting device name into document

```python
# via database class
new_db_1.write({'name': {'first': 'Thom', 'last': 'Yorke'}, 'age': 51, 'band': 'Radiohead'})

# via decorator
from TetherDB import tether

@tether() # No arguments uses default filepath and device_id added to documents
def test_func(name: str, band: str, age: int):
    return dict(name=name, band=band, age=age)
test_func('Jeff Tweedy', 'Wilco', 53)


@tether(db_filepath='test.db', device_id='generic-esp')
def test_func(name: str, band: str, age:int):
    return dict(name=name, band=band, age=age)

test_func('Adam Granduciel', 'The War On Drugs', 41)
```

> **Read:**

&nbsp;&nbsp;*read(document_id: int = 0, iso_8601: bool = True, query_all: bool = False) → Union[dict, Generator]*

- Reading 1 document via document_id argument returns a document(dict)
- Optionally return timestamp in iso8601 format(default) or time since MicroPython epoch(2000-01-01 00:00:00 UTC)

```python
#read 1 document :: Returns Dict
new_db_1.read(5965830)
```
*output:*
```
{
  'name': {
    'first': 'Thom',
    'last': 'Yorke'
  },
  'device_id': 'esp8266-device',
  'document_id': '5965830',
  'band': 'Radiohead',
  'age': 51,
  'timestamp': '2020-09-25T14:49:00+00:00'
}
```
```python
new_db_1.read(query_all=True) :: Returns Generator of all database documents
```

> **Filter:**

&nbsp;&nbsp;*filter(\*\*kwargs) → Union[Generator,None]*

- Accepts keyword arguments. Searches documents for all matches as an AND statement
- Accepts trailing wildcards within string
- Accepts nested object search via '__' delimeter
- Returns a generator or None if 0 matches found
<br>

```python
#Single value
query = new_db_1.filter(age=51)
[i for i in query]
```
*output:*
```
[{
  'name': {
    'first': 'Thom',
    'last': 'Yorke'
  },
  'device_id': 'esp8266-device',
  'document_id': '5965830',
  'band': 'Radiohead',
  'age': 51,
  'timestamp': '2020-09-25T14:49:00+00:00'
}]
```
```python
# Multiple keywords - Returns same result
new_db_1.filter(age=51, band='Radiohead')

#wildcard - Returns same result
new_db_1.filter(band='Radio*')

#nested - Returns same result
new_db_1.filter(name__first='Thom')

#wildcard for int
query = new_db_1.filter(age='5*')
[i for i in query]
```
*output:*
```
[{
  '_id': '3430494',
  'band': 'Wilco',
  'device_id': 'esp8266-device',
  'name': {
    'first': 'Jeff',
    'last': 'Tweedy'
  },
  'timestamp': '2020-09-25T16:40:10+00:00',
  'age': 53
},
{
  '_id': '5965830',
  'band': 'Radiohead',
  'device_id': 'esp8266-device',
  'name': {
    'first': 'Thom',
    'last': 'Yorke'
  },
  'timestamp': '2020-09-25T14:49:00+00:00,
  'age': 51
}]
```

> **Delete:**

&nbsp;&nbsp;*delete(document_id: int, drop_all: bool = False) → str*

- Delete 1 or all documents in database
- Returns string message for # of documents deleted

```python
# via _id
new_db_1.delete(5965830)
>>> '1 documents deleted'

# delete all
new_db_1.delete(drop_all=True)
>>> '15 documents deleted'
```

> **Cleanup:**

&nbsp;&nbsp;*cleanup(seconds: int = None) -> str:*

- Delete all documents with a timestamp beyond specified seconds from time of function call.
- Returns string message for # of documents deleted
```python
new_db_1.cleanup(120)
>>> '1 documents deleted'
```

Additional shortcuts:
```python
len(new_db_1) -> int # of documents in database
new_db_1[<_id>] -> dict # get document with _id
del new_db_1[<_id>] -> None # delete document with _id
```
