from typing import Any, Dict, Iterable

import ray

from kedro.io import AbstractDataSet, DataCatalog, MemoryDataSet
from kedro.pipeline.node import Node
from kedro.symphony.executor.executor import AbstractExecutor


# assert type(f) == ray.remote_function.RemoteFunction

class RayExecutor(AbstractExecutor):
    def __init__(self, nodes: Iterable[Node], is_async: bool = False):
        """Instantiates the executor class.

        Args:
            nodes: The iterable of nodes to run.
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.

        """
        super().__init__(nodes, is_async=is_async)
        self._ray_config: Dict[str, Any] = {}  # TODO: Jiri - conf from YAML
        ray.init(ignore_reinit_error=True, num_cpus=8, num_gpus=1)

    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set

        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        return MemoryDataSet(ds_name)

    def _run(
        self, nodes: Iterable[Node], catalog: DataCatalog, run_id: str = None
    ) -> None:
        """
        This doesn't do _any_ hooks at the moment
        """
        # check that the node function is a ray function
        node_funcs = [node.func for node in nodes]
        decorated_node_funcs = []
        result_ids = []
        for _f in node_funcs:
            if type(_f) == ray.remote_function.RemoteFunction:
                decorated_node_funcs.append(_f)
            else:
                decorated_node_funcs.append(ray.remote(_f))

        for _df, _node in zip(decorated_node_funcs, nodes):
            materialized_inputs = [catalog.load(_input) for _input in _node.inputs]
            result_ids.append(_df.remote(*materialized_inputs))  # submit (non-blocking)

        results = ray.get(result_ids)  # blocking

        for _res, _node in zip(results, nodes):
            for _output in _node.outputs:
                catalog.save(_output, _res)
