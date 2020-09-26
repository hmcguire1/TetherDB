# TetherDB

## TetherDB is a simple document database for MicroPython.
---
*A pure python library written for resource-limited devices such as ESP8266 & ESP32.*
<br>

> Features:
- Simple syntax
- Works natively with MicroPython.
- Easily integrates into existing projects
- Maintain multiple databases on a single device
- Write and query nested objects

Installation
---
- Requires a library such as rshell to copy directory onto device
[rshell - GitHub](https://github.com/dhylands/rshell)

```sh
git clone https://github.com/hmcguire1/TetherDB
cd TetherDB
rshell -p /dev/ttyUSB0
rsync TetherDB /pyboard/TetherDB
```
Configuration
---
> Configuration filepath: TetherDB/config.json
- device_id(str): Add a custom device_id attribute to documents. Default -- {sys.platform}-device
- utc_offset(str): Add utc_offset to timestamp (&#177;dd:dd): Default -- '+00:00'
- cleanup_seconds(int): Add an integer to call cleanup function with no arguments.

Usage
---
> Database Class:
&nbsp;&nbsp;
Database(db_filepath: str = 'TetherDB/Tether.db') - > None

```python
from TetherDB.db import Database
new_db_1 = Database() #Default filepath of ('TetherDB/Tether.db')
new_db_2 = Database('test.db') #root dir

str(new_db_1)
>>> 'Database(db_filepath=TetherDB/Tether.db, db_len=0, utc_offset=None, cleanup_seconds=None)'

>>> str(new_db_2)
'Database(db_filepath=test.db, db_len=0, utc_offset=None, cleanup_seconds=None)'
```
<br>

> Write:
&nbsp;&nbsp;
write(document: dict, device_id: bool = True) → None

- Two methods of writing. Via instantiated database object or utils.tether decorator
- Accepts a Dict type for document
- device_id accepts bool type for injecting device name into document

```python
# via database class
new_db_1.write({'name': {'first': 'Thom', 'last': 'Yorke'}, 'age': 51, 'band': 'Radiohead'})

# via decorator
from TetherDB.utils import tether

@tether() # No arguments uses default filepath and device_id added to documents
def test_func(name: str, band: str):
    return dict(name=name, band=band)
test_func('Adam Granduciel', 'The War On Drugs')

@tether(db_filepath='test.db', device_id='generic-esp')
def test_func(name: str, band: str):
    return dict(name=name, band=band)

test_func('Jeff Tweedy', 'Wilco')
```
<br>

> Read:
&nbsp;&nbsp;
read(document_id: str = '', iso_8601: bool = True, query_all: bool = False) → Union[dict, Generator]

- Reading 1 document via doc_id returns dict
- optionally return timestamp in iso8601 formate(default) or time since Micropython epoch
(2000-01-01 00:00:00 UTC)

```python
#read 1 document :: Returns Dict
new_db_1.read('I2038')
>>> {'name': {'first': 'Thom', 'last': 'Yorke'}, 'device_id': 'esp8266-device', 'timestamp': '2020-09-25T14:49:00-06:00', 'id': 'I2973', 'band': 'Radiohead', 'age': 51}

new_db_1.read(query_all=True) :: Returns Generator of all database documents
```
<br>

> Filter:
<br>
&nbsp;&nbsp;
filter(**kwargs) → Union[Generator,None]

- Returns a generator or None if 0 matches
- Accepts keyword arguments. Searches documents for all matches as an AND statement
- accepts trailing wildcards within string
- accepts nested object search via '__' delimeter
<br>

```python
#Single value
query = new_db_1.filter(age=51)
[i for i in query]

>>> [{'name': {'first': 'Thom', 'last': 'Yorke'}, 'device_id': 'esp8266-device', 'timestamp': '2020-09-25T14:49:00+00:00', '_id': 'I2973', 'band': 'Radiohead', 'age': 51}]

# Multiple keywords = Returns same result
new_db_1.filter(age=51, band='Radiohead')

#wilcard - Returns same result
new_db_1.filter(band='Radio*')

#nested - Returns same result
new_db_1.filter(name__first='Thom')

#wilcard for int
query = new_db_1.filter(age='5*')
[i for i in query]

>>> #sorted for display. MicroPython json does not have a sort_keys argument.
[
    {
		'_id': 'I2782',
		'age': 53,
		'band': 'Wilco',
		'device_id': 'esp8266-device',
		'name': {
			'first': 'Jeff',
			'last': 'Tweedy'
		},
		'timestamp': '2020-09-25T16:40:10+00:00'
	},
	{
		'_id': 'I2973',
		'age': 51,
		'band': 'Radiohead',
		'device_id': 'esp8266-device',
		'name': {
			'first': 'Thom',
			'last': 'Yorke'
		},
		'timestamp': '2020-09-25T14:49:00+00:00'
	}
]
```
<br>

> Delete:
&nbsp;&nbsp;
delete(doc_id: str = '', drop_all: bool = False) → str

- Delete 1 or all documents in database
- Returns string message for # of documents deleted

```python
# via doc_id
new_db_1.delete('I2038')
>>> '1 documents deleted'

# delete all
new_db_1.delete(drop_all=True)
>>> '15 documents deleted'
```
<br>

> Cleanup:
&nbsp;&nbsp;
cleanup(seconds: int = None) -> str:

- Delete all documents with a timestamp beyond specified seconds from time of function call.
- Returns string message for # of documents deleted
```python
new_db_1.cleanup(120)
>>> '1 documents deleted'
```