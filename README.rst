.. image:: https://i.ibb.co/JsZqM7z/snakesist-logo.png
    :target: https://snakesist.readthedocs.io

snakesist
=========

.. image:: https://badge.fury.io/py/snakesist.svg
    :target: https://badge.fury.io/py/snakesist

.. image:: https://readthedocs.org/projects/snakesist/badge/?version=latest
    :target: https://snakesist.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.org/03b8/snakesist.svg?branch=master
    :target: https://travis-ci.org/03b8/snakesist


``snakesist`` is a Python database interface for `eXist-db <https://exist-db.org>`_.
It supports basic CRUD operations and uses `delb <https://delb.readthedocs.io>`_ for representing the yielded resources.

.. code-block:: shell

    pip install snakesist

``snakesist`` allows you to access individual documents from the database using a ``delb.Document`` object, either by simply passing a URL

.. code-block:: python

    >>> from delb import Document

    >>> manifest = Document("existdb://admin:@localhost:8080/exist/db/manifestos/dada_manifest.xml")
    >>> [header.full_text for header in manifest.xpath("//head")]
    ["Hugo Ball", "Das erste dadaistische Manifest"]

or by passing a relative path to the document along with a database client which you can subsequently reuse

.. code-block:: python

    >>> from snakesist import ExistClient

    >>> my_local_db = ExistClient(host="localhost", port=8080, user="admin", password="", root_collection="/db/manifests")
    >>> dada_manifest = Document("dada_manifest.xml", existdb_client=my_local_db)
    >>> [header.full_text for header in dada_manifest.xpath("//head")]
    ["Hugo Ball", "Das erste dadaistische Manifest"]
    >>> communist_manifest = Document("communist_manifest.xml", existdb_client=my_local_db)
    >>> communist_manifest.xpath("//head").first.full_text
    "Manifest der Kommunistischen Partei"


and not only for accessing individual documents, but also for querying data across multiple documents

.. code-block:: python

    >>> all_headers = my_local_db.xpath("//*:head")
    >>> [header.node.full_text for header in all_headers]
    ["Hugo Ball", "Das erste dadaistische Manifest", "Manifest der Kommunistischen Partei", "I. Bourgeois und Proletarier.", "II. Proletarier und Kommunisten", "III. Sozialistische und kommunistische Literatur", "IV. Stellung der Kommunisten zu den verschiedenen oppositionellen Parteien"]

You can of course also modify and store documents back into the database or create new ones and store them.


Your eXist instance
-------------------

``snakesist`` leverages the
`eXist RESTful API <https://www.exist-db.org/exist/apps/doc/devguide_rest.xml>`_
for database queries. This means that allowing database queries using the
``_query`` parameter of the RESTful API is a requirement in the used eXist-db
backend. eXist allows this by default, so if you haven't configured your
instance otherwise, don't worry about it.

Please note that ``snakesist`` is tested with eXist 4.7.1 and is not compatible yet
with version 5. The bug preventing ``snakesist`` to be compatible with the newest major eXist
version will be fixed with the release of eXist 5.3.0.
