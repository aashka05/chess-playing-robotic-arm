"""The YOLO weights path and the class-id -> piece mapping."""

import pytest

from vision import map_pieces_to_squares as m


def test_model_path_is_the_merged_from_scratch2_weights():
    assert m.MODEL_PATH.is_absolute()
    assert m.MODEL_PATH == m.PROJECT_ROOT / "runs/detect/merged-from-scratch2/weights/best.pt"
    assert m.require_model_path() == m.MODEL_PATH
    assert m.MODEL_PATH.is_file()


def test_missing_weights_fail_loudly(tmp_path):
    with pytest.raises(FileNotFoundError, match="YOLO weights not found"):
        m.require_model_path(tmp_path / "nope.pt")


def test_class_names_come_from_the_model():
    names = {0: "white-pawn", 1: "black_KING"}
    assert m.class_name(names, 0) == "white_pawn"
    assert m.class_name(names, 1) == "black_king"
    assert m.class_name(names, 7) is None
    assert m.class_name(["black_bishop"], 0) == "black_bishop"


def test_unexpected_classes_are_rejected():
    m.check_class_names(dict(enumerate(m.CLASS_NAMES)))
    with pytest.raises(ValueError, match="do not match"):
        m.check_class_names({0: "piece", 1: "empty"})


def test_loaded_model_has_the_twelve_pieces():
    pytest.importorskip("ultralytics")
    model = m.load_model()
    assert {m.class_name(model.names, i) for i in model.names} == set(m.CLASS_NAMES)
