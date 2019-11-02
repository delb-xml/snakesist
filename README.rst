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


Usage example
-------------

.. code-block:: python

    from snakesist import ExistClient

    db = ExistClient()

    db.root_collection = '/db/foo/bar'
    # the client will only query from this point downwards

    names = db.retrieve_resources('//*:persName')
    # note the namespace wildcard in the XPath expression

    # append 'Python' to all names which are 'Monty' and delete the rest
    for name in names:
        if name.node.full_text == 'Monty':
            name.node.append_child(' Python')
            name.update_push()
        else:
            name.delete()


Your eXist instance
-------------------

``snakesist`` leverages the
`eXist RESTful API <https://www.exist-db.org/exist/apps/doc/devguide_rest.xml>`_
for database queries. This means that allowing database queries using the
``_query`` parameter of the RESTful API is a requirement in the used eXist-db
backend. eXist allows this by default, so if you haven't configured your
instance otherwise, don't worry about it.

``snakesist`` is tested with eXist 4.7.1 and is not compatible yet with eXist 5.0.0.
