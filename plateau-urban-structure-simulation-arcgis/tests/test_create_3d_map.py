import os

import pytest

from Simulation.Tool import create_3d_map


def test_get_year():
    assert create_3d_map.get_year(r"C:\path\to\A\Building2021.csv") == "2021"
    assert create_3d_map.get_year(r"C:\path\to\A\Building_2022.csv") == "2022"
    # different extension.
    assert create_3d_map.get_year(r"C:\path\to\A\Building_2022.txt") == ""
    # is not year.
    assert create_3d_map.get_year(r"C:\path\to\A\Building_202.csv") == ""


def test_comparetype_get_symbol():
    for comptype, filename in (
        (
            create_3d_map.CompareTypes.change_of_building_usage,
            "symbol_building_usage.lyrx",
        ),
        (
            create_3d_map.CompareTypes.change_of_building_existence,
            "symbol_building_existence.lyrx",
        ),
        (
            create_3d_map.CompareTypes.change_of_building_height,
            "symbol_building_height.lyrx",
        ),
    ):
        res = comptype.get_symbol()
        assert res.filepath == str(
            create_3d_map.SYMBOL_LAYER_HOST_DIR.joinpath(filename)
        )
        assert res.field == (
            "VALUE_FIELD " f"{comptype.name} " f"{comptype.name}"
        )


def test_set_output_layer_name():
    res = create_3d_map.InputParam(
        r"C:\path\to\obj\Building2020.csv",
        r"C:\path\to\sbj\Building2040.csv",
        create_3d_map.CompareTypes.change_of_building_existence.value,
    ).get_output()
    assert res.fc_path == os.path.join(
        str(create_3d_map.OUT_GDB_PATH),
        (
            f"{create_3d_map.CompareTypes.change_of_building_existence.value}"
            "_obj_2020_sbj_2040"
        ),
    )
    assert res.layer_file == os.path.join(
        str(create_3d_map.OUT_LYRX_DIR),
        (
            f"{create_3d_map.CompareTypes.change_of_building_existence.value}"
            "-obj-2020-sbj-2040.lyrx"
        ),
    )


def test_compare_usage():
    assert create_3d_map.compare_usage("変わらない") == "変わらない"
    assert create_3d_map.compare_usage("空地→住宅") == "空地→住宅"
    for x in [
        "空地→共同住宅",
        "空地→商業施設",
        "空地→店舗等併用共同住宅",
        "空地→店舗等併用住宅",
    ]:
        assert create_3d_map.compare_usage(x) == "空地→住宅以外"
    for x in [
        "共同住宅→空地",
        "住宅→空地",
        "商業施設→空地",
        "店舗等併用共同住宅→空地",
        "店舗等併用住宅→空地",
    ]:
        assert create_3d_map.compare_usage(x) == "空地になる"
    for x in [
        "住宅→共同住宅",
        "住宅→商業施設",
        "住宅→店舗等併用共同住宅",
        "住宅→店舗等併用住宅",
    ]:
        assert create_3d_map.compare_usage(x) == "住宅→住宅以外"
    for x in [
        "共同住宅→住宅",
        "商業施設→住宅",
        "店舗等併用共同住宅→住宅",
        "店舗等併用住宅→住宅",
    ]:
        assert create_3d_map.compare_usage(x) == "住宅以外→住宅"
    for x in [
        "共同住宅→商業施設",
        "共同住宅→店舗等併用共同住宅",
        "共同住宅→店舗等併用住宅",
        "商業施設→共同住宅",
        "商業施設→店舗等併用共同住宅",
        "商業施設→店舗等併用住宅",
        "店舗等併用共同住宅→共同住宅",
        "店舗等併用共同住宅→商業施設",
        "店舗等併用共同住宅→店舗等併用住宅",
        "店舗等併用住宅→共同住宅",
        "店舗等併用住宅→商業施設",
        "店舗等併用住宅→店舗等併用共同住宅",
    ]:
        assert create_3d_map.compare_usage(x) == "住宅以外→住宅以外"


@pytest.mark.parametrize(
    ("obj", "sbj", "expected"),
    [
        (412, 402, "共同住宅→商業施設"),
        (412, 413, "共同住宅→店舗等併用住宅"),
        (412, 414, "共同住宅→店舗等併用共同住宅"),
        (412, 411, "共同住宅→住宅"),
        (412, 412, "変わらない"),
        (412, None, "共同住宅→空地"),
        (None, 402, "空地→商業施設"),
        (None, 413, "空地→店舗等併用住宅"),
        (None, 414, "空地→店舗等併用共同住宅"),
        (None, 411, "空地→住宅"),
        (None, 412, "空地→共同住宅"),
        (None, None, "変わらない"),
        (411, 402, "住宅→商業施設"),
        (411, 413, "住宅→店舗等併用住宅"),
        (411, 414, "住宅→店舗等併用共同住宅"),
        (411, 411, "変わらない"),
        (411, 412, "住宅→共同住宅"),
        (411, None, "住宅→空地"),
        (402, 402, "変わらない"),
        (402, 413, "商業施設→店舗等併用住宅"),
        (402, 414, "商業施設→店舗等併用共同住宅"),
        (402, 411, "商業施設→住宅"),
        (402, 412, "商業施設→共同住宅"),
        (402, None, "商業施設→空地"),
        (414, 402, "店舗等併用共同住宅→商業施設"),
        (414, 413, "店舗等併用共同住宅→店舗等併用住宅"),
        (414, 414, "変わらない"),
        (414, 411, "店舗等併用共同住宅→住宅"),
        (414, 412, "店舗等併用共同住宅→共同住宅"),
        (414, None, "店舗等併用共同住宅→空地"),
        (413, 402, "店舗等併用住宅→商業施設"),
        (413, 413, "変わらない"),
        (413, 414, "店舗等併用住宅→店舗等併用共同住宅"),
        (413, 411, "店舗等併用住宅→住宅"),
        (413, 412, "店舗等併用住宅→共同住宅"),
        (413, None, "店舗等併用住宅→空地"),
        # 商業系複合施設（404）は商業施設（402）と同じ扱いとする。
        (412, 404, "共同住宅→商業施設"),
        (None, 404, "空地→商業施設"),
        (411, 404, "住宅→商業施設"),
        (402, 404, "変わらない"),
        (404, 402, "変わらない"),
        (404, 404, "変わらない"),
        (404, 413, "商業施設→店舗等併用住宅"),
        (404, 414, "商業施設→店舗等併用共同住宅"),
        (404, 411, "商業施設→住宅"),
        (404, 412, "商業施設→共同住宅"),
        (404, None, "商業施設→空地"),
        (414, 404, "店舗等併用共同住宅→商業施設"),
        (413, 404, "店舗等併用住宅→商業施設"),
    ],
)
def test_compare_usage_detail(obj, sbj, expected):
    assert create_3d_map.compare_usage_detail(obj, sbj) == expected
