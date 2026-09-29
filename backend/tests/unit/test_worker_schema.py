import pytest
from pydantic import ValidationError

from app.modules.workforce.schema import WorkerCreate


def build(**overrides) -> WorkerCreate:
    fields = {"name": "Maria Lopez", "type": "human", "speed": 1.2}
    fields.update(overrides)
    return WorkerCreate(**fields)


def test_name_whitespace_is_tidied():
    assert build(name="  Maria   Lopez ").name == "Maria Lopez"


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_is_rejected(name):
    with pytest.raises(ValidationError):
        build(name=name)


@pytest.mark.parametrize("position", [{"cur_x": 20}, {"cur_y": 12}, {"cur_x": -1}])
def test_position_must_be_on_the_20_by_12_grid(position):
    with pytest.raises(ValidationError):
        build(**position)


@pytest.mark.parametrize("field, value", [("type", "drone"), ("status", "asleep"), ("speed", 0)])
def test_unknown_values_are_rejected(field, value):
    with pytest.raises(ValidationError):
        build(**{field: value})
