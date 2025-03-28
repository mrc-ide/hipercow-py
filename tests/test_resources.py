import math

import pytest

from hipercow.resources import ClusterResources, Queues, TaskResources


def test_can_construct_simple_queues():
    x = Queues.simple("foo")
    assert x == Queues({"foo"}, "foo", "foo", "foo")


def test_can_construct_real_queues():
    x = Queues({"a", "b", "c", "d"}, build="b", test="c", default="d")
    assert x.valid == {"a", "b", "c", "d"}
    assert x.test == "c"
    assert x.build == "b"
    assert x.default == "d"


def test_throw_if_queues_are_invalid():
    with pytest.raises(ValueError, match="Build queue 'build' is not"):
        Queues({"a", "b"}, build="build", test="a", default="b")


def test_can_check_user_queue():
    x = Queues({"a", "b", "c", "d"}, build="b", test="c", default="d")
    assert x.validate_queue("a") == "a"
    assert x.validate_queue(None) == "d"
    assert x.validate_queue(".default") == "d"
    assert x.validate_queue(".test") == "c"
    with pytest.raises(ValueError, match="Invalid special queue '.foo'"):
        x.validate_queue(".foo")
    with pytest.raises(ValueError, match="'foo' is not in valid queue list"):
        x.validate_queue("foo")


def test_can_create_resources():
    r = TaskResources()
    assert r.queue is None
    assert r.cores == 1
    assert not r.exclusive
    assert r.max_runtime is None
    assert r.memory_per_node is None
    assert r.memory_per_task is None


def test_can_create_non_default_resources():
    r = TaskResources(
        queue="foo",
        cores=16,
        exclusive=True,
        max_runtime=3600,
        memory_per_node=16,
        memory_per_task=8,
    )
    assert r.queue == "foo"
    assert r.cores == 16
    assert r.exclusive
    assert r.max_runtime == 3600
    assert r.memory_per_node == 16
    assert r.memory_per_task == 8


def test_that_cores_is_positive():
    with pytest.raises(ValueError, match="'cores' must be positive"):
        TaskResources(cores=-1)


def test_that_cores_must_be_integer_or_inf():
    assert TaskResources(cores=math.inf).cores == math.inf
    assert TaskResources(cores=100).cores == 100
    with pytest.raises(ValueError, match="'cores' must be an integer"):
        TaskResources(cores=1.5)


def test_can_validate_resources_against_cluster():
    r = ClusterResources(Queues.simple("default"), max_cores=4, max_memory=256)

    res = r.validate_resources(TaskResources(cores=4, memory_per_node=256))
    assert res == TaskResources(queue="default", cores=4, memory_per_node=256)

    with pytest.raises(ValueError, match="Queue 'foo' is not in valid"):
        r.validate_resources(TaskResources(queue="foo"))

    with pytest.raises(ValueError, match="8 is too many cores"):
        r.validate_resources(TaskResources(cores=8))

    with pytest.raises(ValueError, match="512Gb per task is too large"):
        r.validate_resources(TaskResources(memory_per_task=512))

    with pytest.raises(ValueError, match="257Gb per node is too large"):
        r.validate_resources(TaskResources(memory_per_node=257))
