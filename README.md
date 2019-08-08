# snakesist

Snakesist is an experimental library that can be used to connect
to an eXist database instance, load XML documents, iterate over them,
manipulate and save them. It uses [`delb`](https://delb.readthedocs.io/en/latest/)
for accessing the document nodes.

Snakesist doesn't have a stable release yet; please use with care. Contributions are welcome.

`pip install snakesist`

## Usage example

```python
    from snakesist.connector import ExistInstance, NSD_XML as xml, NSD_TEI as tei

    db = ExistInstance(
        url='https://my.existdbinstance.org/exist/',
        usr='foo_bar',
        pw='f0ob4r'
    )

    db.root_collection = '/db/letters/'

    db.load_all_documents()

    for doc in db.documents:
        print(doc.node.root[f'{xml}id'])
```
