import logging
import os
import pathlib
import subprocess
from typing import Callable, Optional

import arcpy

# パス設定用
CURRENT_DIR = pathlib.Path(__file__)
# ベースのパスを取得
BASE_PATH = str(CURRENT_DIR.parents[2])
# InputDataGenerationディレクトリのパス
INPUT_DATA_GEN_DIR = str(CURRENT_DIR.parents[1])
BASE_DATA_PATH = os.path.join(BASE_PATH, r"Simulation\BaseData")
BASE_GDB_PATH = os.path.join(
    BASE_DATA_PATH,
    "BaseData.gdb",
)
ZONE_POLY_FC_NAME = "Zone_Polygon"
ZONE_FC_NAME = "ZoneData"
LOG_PATH = os.path.join(
    INPUT_DATA_GEN_DIR, "Tool", "Logs", "InputDataCreation.log"
)


def create_logger(name: str) -> logging.Logger:
    """ログの設定。"""
    logger = logging.getLogger(name)
    logger.disabled = False
    logger.setLevel(logging.INFO)
    if len(logger.handlers) == 0:
        handler = logging.FileHandler(LOG_PATH)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(handler)
    return logger


def f(
    name: str, size: int, type: str, src: str, alias: Optional[str] = None
) -> str:
    return (
        f'{name} "{alias or name}" true true false {size} {type} 0 0,'
        f"First,#,{src},{name},-1,-1"
    )


def zone_code_field(src: str) -> str:
    return f("zone_code", 8000, "Text", src)


def zone_faciliy_num_map(src: str) -> str:
    return ";".join(
        [
            zone_code_field(src),
            f("fnum_Library", 8, "Long", src, alias="図書館の数"),
            f("fnum_Hospital", 8, "Long", src, alias="病院の数"),
            f("fnum_Clinic", 8, "Long", src, alias="診療所の数"),
            f("fnum_ElementarySchool", 8, "Long", src, alias="小学校の数"),
            f("fnum_MiddleSchool", 8, "Long", src, alias="中学校の数"),
            f("fnum_PreSchool", 8, "Long", src, alias="幼稚園及びこども園の数"),
        ]
    )


def zone_map(src: str) -> str:
    return ";".join(
        [
            zone_code_field(src),
            # f("UseDistrict", 8000, "Text", src),
            f("floorAreaRate", 8, "Long", src, alias="最大容積率"),
            f("buildingCoverageRate", 8, "Long", src, alias="最大建蔽率"),
        ]
    )


def create_control_input(epsg: str) -> None:
    file_name = os.path.join(INPUT_DATA_GEN_DIR, "Control_Input.txt")
    with open(file_name, mode="w", encoding="cp932") as f:
        f.writelines(
            "\n".join(
                [
                    os.path.join(INPUT_DATA_GEN_DIR, "Input"),
                    BASE_DATA_PATH,
                    epsg,
                ]
            )
        )


def basename(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def csv_to_gdb(src: str, field_mapping: Optional[str] = None) -> str:
    res = os.path.join(
        BASE_GDB_PATH,
        basename(src),
    )
    arcpy.conversion.ExportTable(
        src,
        res,
        field_mapping=field_mapping,
    )
    return res


def join_table(target: str, data: str) -> None:
    tmp = os.path.join(BASE_GDB_PATH, f"tmp_{ZONE_FC_NAME}")
    joined = arcpy.management.AddJoin(
        in_layer_or_view=target,
        in_field="zone_code",
        join_table=data,
        join_field="zone_code",
        join_type=False,
    )
    arcpy.management.CopyFeatures(joined, tmp)
    prefix = basename(data)
    format_zone_polygon(tmp, prefix)
    arcpy.management.CopyFeatures(tmp, target)


def remove_prefix(field, prefix: str, src: str) -> None:
    arcpy.management.AlterField(
        src, field.name, field.name.lstrip(f"{prefix}_")
    )


def format_field(field, prefix: str, src: str) -> None:
    if field.name.startswith(f"{ZONE_POLY_FC_NAME}_"):
        remove_prefix(field, ZONE_POLY_FC_NAME, src)
        return

    if (
        field.name == f"{prefix}_OBJECTID"
        or field.name == f"{prefix}_zone_code"
    ):
        arcpy.DeleteField_management(src, [field.name])
        return

    if field.name.startswith(f"{prefix}_"):
        remove_prefix(field, prefix, src)
        return

    if field.name.startswith(f"{ZONE_FC_NAME}_"):
        remove_prefix(field, ZONE_FC_NAME, src)
        return


def format_zone_polygon(src: str, prefix: str) -> None:
    """
    テーブル結合したときについた余計なprefixやフィールドを削除する。
    """
    fields = arcpy.ListFields(src)
    for field in fields:
        format_field(field, prefix, src)


def join_csv(
    filename: str,
    target: str,
    mapper: Callable[
        [
            str,
        ],
        str,
    ],
) -> None:
    path = os.path.join(BASE_DATA_PATH, filename)
    if not os.path.isfile(path):
        return
    data = csv_to_gdb(path, field_mapping=mapper(path))
    join_table(target, data)


def join_csvs(
    zone_poly_fc: str,
    dest_fc: str,
    csvs: list[tuple[str, Callable[[str], str]]],
) -> None:
    arcpy.management.CopyFeatures(zone_poly_fc, dest_fc)
    for filename, fn in csvs:
        join_csv(filename, dest_fc, fn)


def get_current_map():
    active_project = arcpy.mp.ArcGISProject("CURRENT")
    for map in active_project.listMaps():
        if map.mapType == "SCENE":
            return map


def create_zone_fc(zone_poly_fc: str, dest: str) -> None:
    join_csvs(
        zone_poly_fc,
        dest,
        [
            ("Zone_FacilityNum.csv", zone_faciliy_num_map),
            ("Zone.csv", zone_map),
        ],
    )
    get_current_map().addDataFromPath(dest)


def main(
    epsg: str,
    zone_data_gen: bool = True,
    dist_zone_facility_gen: bool = True,
    inidividual_gen: bool = True,
    transportation_data_gen: bool = True,
) -> None:
    create_control_input(epsg)

    if zone_data_gen:
        # ゾーンデータ作成機能を実行
        excute("ZoneDataGeneration.exe")
    if dist_zone_facility_gen:
        # 施設平均距離付与機能を実行
        excute("DistZoneFacilityDataGeneration.exe")
    if inidividual_gen:
        # 個人データ作成機能を実行
        excute("IndividualDataGeneration.exe")
    if transportation_data_gen:
        # 交通データ作成機能を実行
        excute("TransportationDataGeneration.exe")
    zone_poly_fc = os.path.join(BASE_GDB_PATH, ZONE_POLY_FC_NAME)
    if arcpy.Exists(zone_poly_fc):
        create_zone_fc(zone_poly_fc, os.path.join(BASE_GDB_PATH, ZONE_FC_NAME))


def excute(exe_file: str) -> None:
    """exeファイルの実行。"""
    result = subprocess.run(
        os.path.join(INPUT_DATA_GEN_DIR, exe_file),
        cwd=INPUT_DATA_GEN_DIR,
        capture_output=True,
        text=True,
    )
    # exeファイル実行時に例外時発生したら、強制終了
    if result.returncode != 0:
        raise Exception(result.stderr)


# 異常ログ出力メソッド
def logging_error(logger: logging.Logger, exception: Exception) -> None:
    logger.error(exception, stack_info=True)
    arcpy.AddError(exception)


if __name__ == "__main__":
    log = create_logger("InputDataCreation.py")
    log.info("処理開始")
    try:
        main(
            epsg=arcpy.GetParameterAsText(0),
            zone_data_gen=arcpy.GetParameterAsText(1) == "true",
            dist_zone_facility_gen=arcpy.GetParameterAsText(2) == "true",
            inidividual_gen=arcpy.GetParameterAsText(3) == "true",
            transportation_data_gen=arcpy.GetParameterAsText(4) == "true",
        )
    except Exception as e:
        logging_error(log, e)
    else:
        log.info("正常に処理が終了しました。")
