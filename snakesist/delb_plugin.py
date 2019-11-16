from types import SimpleNamespace

import pluggy


class ExistResource:
    def _init_config(self, config):
        self.config.exist = SimpleNamespace(
            client=config.pop("exist_client"),
            absolute_id=config.pop("exist_absolute_id", None),
            node_id=config.pop("exist_node_id", None),
            document_path=config.pop("exist_document_path", None)
        )
        super()._init_config(config)

    def update_pull(self):
        """
        Retrieve the current node state from the database and update the object.
        # """
        self.root = self.config.exist.client.retrieve_resource(
            abs_resource_id=self.config.exist.absolute_id,
            node_id=self.config.exist.node_id
        ).root

    def update_push(self):
        self.config.exist.client.update_document(
            data=str(self.root),
            document_path=self.config.exist.document_path,
        )

    def delete(self):
        self.config.exist.client.delete_document(document_path=self.config.exist.document_path)
        self.config.exist.node_id = None
        self.config.exist.absolute_id = None
        self.config.exist.document_path = None


@pluggy.HookimplMarker("delb")
def get_document_extensions():
    return ExistResource
