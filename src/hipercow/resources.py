"""Specify and interact with resources."""

import math
from dataclasses import dataclass

from pydantic import BaseModel, field_validator


class TaskResources(BaseModel):
    """Resources required for a task.

    We don't support everything that the R version does yet; in
    particular we've not set up `hold_until`, `priority` or
    `requested_nodes`, as these are not widely used.

    Attributes:
        queue: The queue to run on.  If not given (or `None`), we use
            the default queue for your cluster.  Alternatively, you
            can provide `.default` for the default queue or `.test`
            for the test queue.

        cores: The number of cores to request.  Adding more cores does
            not necessarily make your task any faster; your task must
            have some mechanism to exploit this parallelism (e.g.,
            using the
            [`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html)
            package).  Specify `math.inf` if you want to request all
            the cores on a single node.

        exclusive: Request exclusive access to a node.

        max_runtime: The maximum run time (wall clock), in seconds.

        memory_per_node: Specify that your task can only run on a node
            with at least this much memory, in GB (e.g, 128 is 128GB).

        memory_per_task: An estimate of how much memory your task
            requires (across all cores), in GB.  If you provide this,
            the scheduler can attempt to arrange tasks such that they
            will all fit in the available RAM.

    """

    queue: str | None = None
    cores: int | float = 1
    exclusive: bool = False
    max_runtime: int | None = None
    memory_per_node: int | None = None
    memory_per_task: int | None = None

    @field_validator("cores")
    @classmethod
    def _require_positive_cores(cls, v: int | float) -> int | float:
        if not isinstance(v, int):
            if v == math.inf:
                return v
            msg = "'cores' must be an integer (or inf)"
            raise ValueError(msg)
        return _require_positive(v, "cores")

    @field_validator("max_runtime")
    @classmethod
    def _require_positive_max_runtime(cls, v: int) -> int:
        return _require_positive(v, "max_runtime")

    @field_validator("memory_per_node")
    @classmethod
    def _require_positive_memory_per_node(cls, v: int) -> int:
        return _require_positive(v, "memory_per_node")

    @field_validator("memory_per_task")
    @classmethod
    def _require_positive_memory_per_task(cls, v: int) -> int:
        return _require_positive(v, "memory_per_task")


@dataclass
class Queues:
    """Queues available on the cluster.

    Attributes:
        valid: The set of valid queue names. Being a set, the order does
            not imply anything.

        default: The default queue, used if none is explicitly given

        build: The queue used to run build jobs

        test: The queue used to run test jobs
    """

    valid: set[str]
    default: str
    build: str
    test: str

    @staticmethod
    def simple(name: str) -> "Queues":
        """Create a `Queues` object with only one valid queue.

        This situation is common enough that we provide a small wrapper.

        Args:
            name: The only supported queue.  This will become the set
                of valid queues, the default queue, the build queue and
                the test queue.
        """
        return Queues({name}, name, name, name)

    def __post_init__(self):
        self._check_queue(self.default, "Default queue")
        self._check_queue(self.build, "Build queue")
        self._check_queue(self.test, "Test queue")

    def _check_queue(self, name: str, description: str = "Queue"):
        if name not in self.valid:
            msg = f"{description} '{name}' is not in valid queue list"
            raise ValueError(msg)

    def validate_queue(
        self, name: str | None, description: str = "Queue"
    ) -> str:
        if name is None:
            return self.default
        if name.startswith("."):
            if name[1:] == "default":
                return self.default
            elif name[1:] == "test":
                return self.test
            else:
                msg = f"Invalid special queue '{name}'"
                raise ValueError(msg)
        self._check_queue(name, description)
        return name


@dataclass
class ClusterResources:
    """Resources available on a cluster.

    This will be returned by a cluster driver and will be used to
    validate resources.

    Attributes:
       queues: Valid queues.
       max_memory: The maximum ram across all nodes in the cluster.
       max_cores: The maximum cores across all nodes in the cluster.

    """

    queues: Queues
    max_cores: int
    max_memory: int

    def validate_resources(self, resources: TaskResources) -> TaskResources:
        """Check resources are valid on this cluster.

        Takes a set of resources and checks that the requested queue,
        number of cores and ram are valid for the cluster.  If the
        queue is not provided, then we will take the default.

        Args:
            resources: Resources to validate.

        """
        resources.queue = self.queues.validate_queue(resources.queue)
        if resources.cores > self.max_cores:
            msg = f"{resources.cores} is too many cores for this cluster"
            raise ValueError(msg)
        _check_ram(resources.memory_per_node, self.max_memory, "node")
        _check_ram(resources.memory_per_task, self.max_memory, "task")

        return resources


def _require_positive(x: int, name: str) -> int:
    if x is not None and x < 0:
        msg = f"'{name}' must be positive"
        raise ValueError(msg)
    return x


def _check_ram(requested: int | None, available: int, type: str):
    if requested is not None and requested > available:
        msg = f"{requested}Gb per {type} is too large for this cluster"
        raise ValueError(msg)
