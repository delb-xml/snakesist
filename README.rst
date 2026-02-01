snakesist
=========

.. image:: https://img.shields.io/pypi/l/snakesist.svg
    :target: https://github.com/delb-xml/snakesist/blob/main/LICENSE.txt
    :alt: License

.. image:: https://img.shields.io/pypi/pyversions/snakesist.svg
    :alt: Python versions

.. image:: https://readthedocs.org/projects/snakesist/badge/?version=latest
    :target: https://snakesist.readthedocs.io/en/latest/
    :alt: Documentation Status


``snakesist`` is a Python database interface for eXist-db_.
It supports basic CRUD operations and uses delb_'s models to represent
documents and nodes.
It's available at the Python Package Index as snakesist_ package.

.. code-block:: shell

    pip install snakesist

``snakesist`` allows you to access individual documents from the database using
a :class:`delb.Document` object, either by simply passing a URL:

.. code-block:: python

    >>> from delb import Document

    >>> manifest = Document(
    ...     "existdb://admin:@localhost:8080/exist/db/manifestos/dada_manifest.xml"
    ... )
    >>> [header.full_text for header in manifest.xpath("//head")]
    ["Hugo Ball", "Das erste dadaistische Manifest"]

or by passing a relative path to the document along with a database client
that is bound to an eXist `documents collection`_ which you can subsequently
reuse:

.. code-block:: python

    >>> from snakesist import ExistClient

    >>> exist_client = ExistClient(
    ...     host="localhost",
    ...     port=8080,
    ...     user="admin",
    ...     password="",
    ...     root_collection="/db/manifestos"
    ... )
    >>> dada_manifest = Document("dada_manifest.xml", existdb_client=exist_client)
    >>> [header.full_text for header in dada_manifest.xpath("//head")]
    ["Hugo Ball", "Das erste dadaistische Manifest"]
    >>> communist_manifest = Document(
    ...     "communist_manifest.xml", existdb_client=exist_client
    ... )
    >>> communist_manifest.xpath("//head").first.full_text
    "Manifest der Kommunistischen Partei"

and not only for accessing individual documents, but also for querying nodes
across multiple documents:

.. code-block:: python

    >>> [header.node.full_text for header in exist_client.xpath("//*:head")]
    ["Hugo Ball", "Das erste dadaistische Manifest", "Manifest der Kommunistischen Partei", "I. Bourgeois und Proletarier.", "II. Proletarier und Kommunisten", "III. Sozialistische und kommunistische Literatur", "IV. Stellung der Kommunisten zu den verschiedenen oppositionellen Parteien"]

You can of course also modify and store documents back into the database or create new ones and store them.


Your eXist instance
-------------------

*snakesist* leverages eXist's `RESTful API`_ for database operations. This
means that allowing database queries using POST requests on the RESTful API is
a requirement in the used eXist-db instance. eXist allows this by default, so
if you haven't configured your instance otherwise, don't worry about it.

We aim to directly support all most recent releases from each major branch.
Yet, there's no guarantee that releases older than two years will be kept as a
target for tests. Pleaser refer to the values
``tool.hatch.envs.tests.matrix.existdb_version`` in the `pyproject.toml`_ for
what's currently considered.



.. _delb: https://delb.readthedocs.io/
.. _documents collection: https://exist-db.org/exist/apps/doc/using-collections
.. _eXist-db: https://exist-db.org/
.. _pyproject.toml: https://github.com/delb-xml/snakesist/blob/main/pyproject.toml
.. _RESTful API: https://www.exist-db.org/exist/apps/doc/devguide_rest.xml
.. _snakesist: https://pypi.org/p/snakesist
