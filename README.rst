snakesist
=========

.. image:: https://badge.fury.io/py/snakesist.svg
    :target: https://badge.fury.io/py/snakesist

.. image:: https://readthedocs.org/projects/snakesist/badge/?version=latest
    :target: https://snakesist.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

``snakesist`` is an experimental Python database driver for `eXist-db <https://exist-db.org>`_.
It currently only supports retrieving, updating and deleting resources.

.. code-block:: shell

    pip install snakesist


Usage example
-------------

.. code-block:: python

    import delb
    from snakesist.exist_client import ExistClient

    db = ExistClient(
        host='my.existdbinstance.org',  # defaults to 'localhost'
        port='80',  # defaults to 8080
        usr='foo_bar',  # defaults to 'admin'
        pw='f0ob4r'  # defaults to ''
    )

    db.root_collection = '/db/foo/bar'
    # the client will only query from this point downwards

    names = db.retrieve_resources('//*:persName')
    # note the namespace wildcard in the XPath expression

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
``_query=`` parameter of the RESTful API is a requirement in the used exist-db
backend. eXist allows this by default, so if you haven't configured your
instance otherwise, don't worry about it.


Stability
---------

This package doesn't have a stable release yet and lacks sufficient test coverage.
Please use with care. It also has `delb <https://delb.readthedocs.io/en/latest/>`_
as a dependency (for representing the yielded resources), which is a very young
project developed as a proof of concept at the moment.

Contributions, suggestions, bug reports and feature requests for ``snakesist``
are more than welcome.
