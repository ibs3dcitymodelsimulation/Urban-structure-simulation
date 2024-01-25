"""
3D可視化機能
"""

import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Optional

import arcpy

# path 指定
ROOT_DIR = Path(__file__).parents[2]
IN_GDB_PATH = ROOT_DIR.joinpath("Simulation", "BaseData", "BaseData.gdb")
TMP_GDB_PATH = ROOT_DIR.joinpath(
    "Output", "Visualization", "Database", "IntermediateData.gdb"
)
OUT_GDB_PATH = ROOT_DIR.joinpath(
    "Output", "Visualization", "Database", "Output.gdb"
)
LOG_PATH = ROOT_DIR.joinpath("Simulation", "Tool", "Logs", "create_3d_map.log")
SYMBOL_LAYER_HOST_DIR = ROOT_DIR.joinpath(
    "Output", "Visualization", "SymbolLayer"
)
OUT_LYRX_DIR = ROOT_DIR.joinpath("Output", "Visualization", "OutputLayer")
BUILDING_PATH = IN_GDB_PATH.joinpath("Building")

RESIDENCE_TYPES = (411,)
OTHER_TYPES = (
    401,
    402,
    403,
    404,
    412,
    413,
    414,
    415,
    421,
    422,
    431,
    441,
    451,
    452,
    453,
    454,
    461,
)
VACANT_TYPES = (None, -1)

# 建築物用途名（詳細塗分け用）
# シミュレーションの対象ではない用途は変わらないため取り扱わない。（変化なしとなる）
VIZ_USAGE_NAMES = {
    # 401: "業務施設",
    402: "商業施設",
    # 403: "宿泊施設",
    # 商業系複合施設（404）は商業施設（402）と同じ扱いとする
    404: "商業施設",  # "商業系複合施設",
    411: "住宅",
    412: "共同住宅",
    413: "店舗等併用住宅",
    414: "店舗等併用共同住宅",
    # 415: "作業所併用住宅",
    # 421: "官公庁施設",
    # 422: "文教厚生施設",
    # 431: "運輸倉庫施設",
    # 441: "工場",
    # 451: "農林漁業用施設",
    # 452: "供給処理施設",
    # 453: "防衛施設",
    # 454: "その他",
    # 461: "不明",
    -1: "空地",
    None: "空地",
}


class CompareTypes(Enum):
    change_of_building_usage = "建築物用途の比較"
    change_of_building_usage_d = "建築物用途の比較_詳細"
    change_of_building_existence = "建築物存在有無の比較"
    change_of_building_height = "建築物高さ差分"

    def get_lyrx_name(self):
        if self == CompareTypes.change_of_building_usage:
            return "symbol_building_usage.lyrx"
        if self == CompareTypes.change_of_building_usage_d:
            return "symbol_building_usage_d.lyrx"
        if self == CompareTypes.change_of_building_existence:
            return "symbol_building_existence.lyrx"
        if self == CompareTypes.change_of_building_height:
            return "symbol_building_height.lyrx"

    def get_symbol(self):
        return Symbology(
            str(SYMBOL_LAYER_HOST_DIR.joinpath(self.get_lyrx_name())),
            f"VALUE_FIELD {self.name} {self.name}",
        )


HEIGHT_FIELDS = [
    "objctvtbl_Height",
    "sbjctvtbl_Height",
    "simulated_building_height",
    "comparison_of_building_height",
    CompareTypes.change_of_building_height.name,
]


class UsageChange(Enum):
    UNCHANGED = "変わらない"
    VACANT_TO_RESIDENCE = "空地→住宅"
    VACANT_TO_OTHER = "空地→住宅以外"
    TO_VACANT = "空地になる"
    RESIDENCE_TO_OTHER = "住宅→住宅以外"
    OTHER_TO_RESIDENCE = "住宅以外→住宅"
    OTHER_TO_OTHER = "住宅以外→住宅以外"


class InputParam:
    def __init__(self, objpath: str, sbjpath: str, casename: str) -> None:
        self.objpath = objpath
        self.sbjpath = sbjpath
        self.casetype = CompareTypes(casename)

    def get_output(self):
        obj_name = os.path.basename(os.path.dirname(self.objpath))
        sbj_name = os.path.basename(os.path.dirname(self.sbjpath))
        year_obj = get_year(self.objpath)
        year_sub = get_year(self.sbjpath)
        return Output(
            str(
                OUT_GDB_PATH.joinpath(
                    "_".join(
                        [
                            self.casetype.value,
                            obj_name,
                            year_obj,
                            sbj_name,
                            year_sub,
                        ]
                    )
                )
            ),
            str(
                OUT_LYRX_DIR.joinpath(
                    "-".join(
                        [
                            self.casetype.value,
                            obj_name,
                            year_obj,
                            sbj_name,
                            year_sub,
                        ]
                    )
                    + ".lyrx",
                )
            ),
        )


class Symbology:
    def __init__(self, filepath: str, field: str) -> None:
        self.filepath = filepath
        self.field = field


class Tables:
    objective_table = None
    subjective_table = None
    visualization_working_table = None
    visualization_table = None


class Output:
    def __init__(self, fc_path: str, layer_file: str) -> None:
        self.fc_path = fc_path
        self.layer_file = layer_file


def main():
    logger = set_log_format("create_3d_map")
    logger.info("Execute function.")
    try:
        init_enviroment()
        params = InputParam(
            arcpy.GetParameterAsText(0),
            arcpy.GetParameterAsText(1),
            arcpy.GetParameterAsText(2),
        )
        output = params.get_output()
        convert_csv_to_table_class(params)
        create_visualization_working_table()
        calculate_fields_value()
        generate_visualization_table()
        create_result_fc(output)
        create_3d_layer_file(params.casetype.get_symbol(), output)
        add_layer_to_map(output)
    except Exception as e:
        logger.error(e, exc_info=True)
        arcpy.AddError(e)
    else:
        logger.info("Complete function.")
        arcpy.AddMessage("3D可視化機能は正常に処理を完了しました。")


# 初期化処理
def init_enviroment():
    logger = set_log_format("init_enviroment")
    logger.info("Start processing.")
    arcpy.management.Delete(str(TMP_GDB_PATH))
    arcpy.management.CreateFileGDB(
        out_folder_path=str(
            ROOT_DIR.joinpath("Output", "Visualization", "Database")
        ),
        out_name="IntermediateData.gdb",
    )
    logger.info("Complete processing.")


def get_year(filename: str):
    matched = re.search(r"(\d{4})\.csv$", filename)
    return str(matched.group(1)) if matched else ""


# CSV→テーブル変換
def convert_csv_to_table_class(params: InputParam):
    logger = set_log_format("convert_csv_to_table_class")
    logger.info("Start processing.")
    objective_table = arcpy.conversion.ExportTable(
        in_table=params.objpath,
        out_table=str(TMP_GDB_PATH.joinpath("objective_table")),
        where_clause="",
        use_field_alias_as_name="NOT_USE_ALIAS",
        field_mapping=(
            'buildingID "buildingID" '
            "true true false 8000 Text 0 0,First,#,"
            f"{params.objpath}"
            ",buildingID,0,8000;"
            #
            'Usage "Usage" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.objpath}"
            ",Usage,-1,-1;"
            #
            'YearOfConstruction "YearOfConstruction" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.objpath}"
            ",YearOfConstruction,-1,-1;"
            #
            'Height "Height" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",Height,-1,-1;"
            #
            'storeysAboveGround "storeysAboveGround" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.objpath}"
            ",storeysAboveGround,-1,-1;"
            #
            'totalFloorArea "totalFloorArea" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",totalFloorArea,-1,-1;"
            #
            'FootprintArea "FootprintArea" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",FootprintArea,-1,-1;"
            #
            'Existing "Existing" '
            "true true false 4 Long 0 0,First,#,"
            f"{params.objpath}"
            ",Existing,-1,-1;"
            #
            'RoadWidth "RoadWidth" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",RoadWidth,-1,-1;"
            #
            'zone_code "zone_code" '
            "true true false 4 Text 0 0,First,#"
            f"{params.objpath}"
            ",zone_code,-1,-1;"
            #
            'BuildingAge "BuildingAge" '
            "true true false 8000 Long 0 0,First,#,"
            f"{params.objpath}"
            ",BuildingAge,0,8000;"
            #
            'Integrated_buildingID "Integrated_buildingID" '
            "true true false 8000 Text 0 0,First,#,"
            f"{params.objpath}"
            ",Integrated_buildingID,0,8000;"
            #
            'SimTargetFlag "SimTargetFlag" '
            "true true false 8000 Long 0 0,First,#,"
            f"{params.objpath}"
            ",SimTargetFlag,0,8000;"
            #
            'Lat "Lat" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",Lat,-1,-1;"
            #
            'Lon "Lon" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.objpath}"
            ",Lon,-1,-1"
        ),
    )
    objective_table_field_names = [
        fn.name for fn in arcpy.ListFields(objective_table)
    ]
    for name in objective_table_field_names:
        new_field_name = "objctvtbl_" + name
        arcpy.management.AlterField(
            in_table=objective_table,
            field=name,
            new_field_name=new_field_name,
            new_field_alias=new_field_name,
        )
    Tables.objective_table = objective_table

    subjective_table = arcpy.conversion.ExportTable(
        in_table=params.sbjpath,
        out_table=str(TMP_GDB_PATH.joinpath("subjective_table")),
        where_clause="",
        use_field_alias_as_name="NOT_USE_ALIAS",
        field_mapping=(
            'buildingID "buildingID" '
            "true true false 8000 Text 0 0,First,#,"
            f"{params.sbjpath}"
            ",buildingID,0,8000;"
            #
            'Usage "Usage" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",Usage,-1,-1;"
            #
            'YearOfConstruction "YearOfConstruction" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",YearOfConstruction,-1,-1;"
            #
            'Height "Height" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",Height,-1,-1;"
            #
            'storeysAboveGround "storeysAboveGround" '
            "true true false 8 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",storeysAboveGround,-1,-1;"
            #
            'totalFloorArea "totalFloorArea" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",totalFloorArea,-1,-1;"
            #
            'FootprintArea "FootprintArea" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",FootprintArea,-1,-1;"
            #
            'Existing "Existing" '
            "true true false 4 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",Existing,-1,-1;"
            #
            'RoadWidth "RoadWidth" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",RoadWidth,-1,-1;"
            #
            'zone_code "zone_code" '
            "true true false 4 Text 0 0,First,#"
            f"{params.sbjpath}"
            ",zone_code,-1,-1;"
            #
            'BuildingAge "BuildingAge" '
            "true true false 8000 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",BuildingAge,0,8000;"
            #
            'Integrated_buildingID "Integrated_buildingID" '
            "true true false 8000 Text 0 0,First,#,"
            f"{params.sbjpath}"
            ",Integrated_buildingID,0,8000;"
            #
            'SimTargetFlag "SimTargetFlag" '
            "true true false 8000 Long 0 0,First,#,"
            f"{params.sbjpath}"
            ",SimTargetFlag,0,8000;"
            #
            'Lat "Lat" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",Lat,-1,-1;"
            #
            'Lon "Lon" '
            "true true false 8 Double 0 0,First,#,"
            f"{params.sbjpath}"
            ",Lon,-1,-1"
        ),
    )
    subjective_table_field_name_list = [
        fn.name for fn in arcpy.ListFields(subjective_table)
    ]
    for name in subjective_table_field_name_list:
        new_name = "sbjctvtbl_" + name
        arcpy.management.AlterField(
            in_table=subjective_table,
            field=name,
            new_field_name=new_name,
            new_field_alias=new_name,
        )
    Tables.subjective_table = subjective_table
    logger.info("Complete processing.")
    arcpy.AddMessage("シミュレーション結果のテーブル変換完了 (1/8)")


# 作業用テーブルの作成
def create_visualization_working_table():
    logger = set_log_format("create_visualization_working_table")
    logger.info("Start processing.")
    addjoin_result = arcpy.management.AddJoin(
        in_layer_or_view=Tables.objective_table,
        in_field="objctvtbl_buildingID",
        join_table=Tables.subjective_table,
        join_field="sbjctvtbl_buildingID",
    )
    visualization_working_table = arcpy.conversion.ExportTable(
        in_table=addjoin_result,
        out_table=str(TMP_GDB_PATH.joinpath("visualization_working_table")),
    )
    arcpy.management.AddFields(
        in_table=visualization_working_table,
        field_description=[
            ["buildingID", "TEXT", "建築物コード"],
            ["simulated_building_usage", "TEXT", "建築物用途"],
            [
                CompareTypes.change_of_building_usage.name,
                "TEXT",
                CompareTypes.change_of_building_usage.value,
            ],
            [
                CompareTypes.change_of_building_usage_d.name,
                "TEXT",
                CompareTypes.change_of_building_usage_d.value,
            ],
            [
                CompareTypes.change_of_building_usage_d.name,
                "TEXT",
                CompareTypes.change_of_building_usage_d.value,
            ],
            [
                CompareTypes.change_of_building_existence.name,
                "TEXT",
                CompareTypes.change_of_building_existence.value,
            ],
            ["simulated_building_height", "DOUBLE", "建築物高さ"],
            [
                "comparison_of_building_height",
                "FLOAT",
                "建築物高さの比較",
            ],
            [
                CompareTypes.change_of_building_height.name,
                "TEXT",
                CompareTypes.change_of_building_height.value,
            ],
        ],
    )
    Tables.visualization_working_table = visualization_working_table
    logger.info("Complete processing.")
    arcpy.AddMessage("作業用テーブル作成完了 (2/8)")


# 作業用テーブルのフィールド値演算
def calculate_fields_value():
    logger = set_log_format("calculate_fields_value")
    logger.info("Start processing.")
    visualization_working_table = Tables.visualization_working_table
    # 建築物コード
    apply_buildingID()
    # 建築物用途
    arcpy.management.CalculateField(
        in_table=visualization_working_table,
        field="simulated_building_usage",
        expression="!sbjctvtbl_Usage!",
        expression_type="PYTHON3",
    )
    # 建築物用途の比較
    set_compared_usage()
    # 建築物存在有無
    classify_existence()
    # 建築物高さ
    calculate_height()
    # 建築物高さの比較
    compare_height()
    # 建築物高さの差分
    classify_height()
    logger.info("Complete processing.")
    arcpy.AddMessage("作業用テーブル計算完了 (3/8)")


# 可視化用テーブルの作成
def generate_visualization_table():
    logger = set_log_format("generate_visualization_table")
    logger.info("Start processing.")
    arcpy.management.DeleteField(
        in_table=Tables.visualization_working_table,
        drop_field=[
            "objctvtbl_buildingID",
            # "objctvtbl_Usage",
            "objctvtbl_YearOfConstruction",
            # "objctvtbl_Height",
            "objctvtbl_storeysAboveGround",
            "objctvtbl_totalFloorArea",
            "objctvtbl_FootprintArea",
            # "objctvtbl_Existing",
            "objctvtbl_RoadWidth",
            "objctvtbl_zone_code",
            "objctvtbl_BuildingAge",
            "objctvtbl_Integrated_buildingID",
            "objctvtbl_SimTargetFlag",
            "objctvtbl_Lat",
            "objctvtbl_Lon",
            "OBJECTID",
            "sbjctvtbl_buildingID",
            # "sbjctvtbl_Usage",
            "sbjctvtbl_YearOfConstruction",
            # "sbjctvtbl_Height",
            "sbjctvtbl_storeysAboveGround",
            "sbjctvtbl_totalFloorArea",
            "sbjctvtbl_FootprintArea",
            # "sbjctvtbl_Existing",
            "sbjctvtbl_RoadWidth",
            "sbjctvtbl_zone_code",
            "sbjctvtbl_BuildingAge",
            "sbjctvtbl_Integrated_buildingID",
            "sbjctvtbl_SimTargetFlag",
            "sbjctvtbl_Lat",
            "sbjctvtbl_Lon",
            "comparison_of_building_height",
        ],
    )
    Tables.visualization_table = arcpy.conversion.ExportTable(
        in_table=Tables.visualization_working_table,
        out_table=str(TMP_GDB_PATH.joinpath("visualization_table")),
    )
    logger.info("Complete processing.")
    arcpy.AddMessage("可視化用テーブル作成完了 (4/8)")


# 3D可視化用フィーチャクラスの作成
def create_result_fc(output: Output):
    logger = set_log_format("create result feature class")
    logger.info("Start processing.")
    if not arcpy.Exists(OUT_GDB_PATH):
        arcpy.management.CreateFileGDB(
            out_folder_path=str(
                ROOT_DIR.joinpath("Output", "Visualization", "Database")
            ),
            out_name="Output.gdb",
        )
    arcpy.conversion.ExportFeatures(
        in_features=str(IN_GDB_PATH.joinpath("Building")),
        out_features=str(output.fc_path),
        where_clause="",
        use_field_alias_as_name=False,
        field_mapping=(
            'buildingID "buildingID" '
            "true true false 255 Text 0 0,First,#,"
            "Building,buildingID,0,255;"
            #
            'Usage "Usage" '
            "true true false 255 Text 0 0,First,#,"
            "Building,Usage,0,255;"
            #
            'YearOfConstruction "YearOfConstruction" '
            "true true false 255 Long 0 0,First,#,"
            "Building,YearOfConstruction,0,255;"
            #
            'Height "Height" '
            "true true false 255 Float 0 0,First,#,"
            "Building,Height,0,255;"
            #
            'storeysAboveGround "storeysAboveGround" '
            "true true false 255 Long 0 0,First,#,"
            "Building,storeysAboveGround,0,255;"
            #
            'totalFloorArea "totalFloorArea" '
            "true true false 255 Double 0 0,First,#,"
            "Building,totalFloorArea,0,255;"
            #
            'FootprintArea "FootprintArea" '
            "true true false 255 Double 0 0,First,#,"
            "Building,FootprintArea,0,255;"
            #
            'Existing "Existing" '
            "true true false 255 Long 0 0,First,#,"
            "Building,Existing,0,255;"
            #
            'RoadWidth "RoadWidth" '
            "true true false 255 Double 0 0,First,#,"
            "Building,RoadWidth,0,255;"
            #
            'zone_code "zone_code" true true false 255 Text 0 0,First,#,'
            "Building,zone_code,0,255;"
            #
            'BuildingAge "BuildingAge" '
            "true true false 4 Long 0 0,First,#,"
            "Building,BuildingAge,-1,-1;"
            #
            'Integrated_buildingID "Integrated_buildingID" '
            "true true false 255 Text 0 0,First,#,"
            "Building,Integrated_buildingID,0,255;"
            #
            'SimTargetFlag "SimTargetFlag" '
            "true true false 4 Long 0 0,First,#,"
            "Building,SimTargetFlag,-1,-1;"
            #
            'Shape_Length "Shape_Length" '
            "false true true 8 Double 0 0,First,#,"
            "Building,Shape_Length,-1,-1;"
            #
            'Shape_Area "Shape_Area" '
            "false true true 8 Double 0 0,First,#,"
            "Building,Shape_Area,-1,-1"
        ),
    )
    arcpy.management.JoinField(
        in_data=str(output.fc_path),
        in_field="buildingID",
        join_table=Tables.visualization_table,
        join_field="buildingID",
        fields=None,
        fm_option="NOT_USE_FM",
        field_mapping=None,
    )
    logger.info("Complete processing.")
    arcpy.AddMessage("可視化用フィーチャクラス作成完了 (6/8)")


# レイヤー ファイルの作成
def create_3d_layer_file(symbol: Symbology, output: Output):
    logger = set_log_format("create_3d_layer_file")
    logger.info("Start processing.")
    building_footprnit_layer = arcpy.management.MakeFeatureLayer(
        in_features=str(output.fc_path),
        out_layer=os.path.splitext(os.path.basename(output.layer_file))[0],
        where_clause="",
        workspace=None,
        field_info=(
            "OBJECTID OBJECTID "
            "VISIBLE NONE;"
            "Shape Shape "
            "VISIBLE NONE;"
            "buildingID buildingID "
            "VISIBLE NONE;"
            "Usage Usage "
            "VISIBLE NONE;"
            "YearOfConstruction YearOfConstruction "
            "VISIBLE NONE;"
            "Height Height "
            "VISIBLE NONE;"
            "storeysAboveGround storeysAboveGround "
            "VISIBLE NONE;"
            "totalFloorArea totalFloorArea "
            "VISIBLE NONE;"
            "FootprintArea FootprintArea "
            "VISIBLE NONE;"
            "Existing Existing "
            "VISIBLE NONE;"
            "RoadWidth RoadWidth "
            "VISIBLE NONE;"
            "zone_code zone_code "
            "VISIBLE NONE;"
            "BuildingAge BuildingAge "
            "VISIBLE NONE;"
            "Integrated_buildingID Integrated_buildingID "
            "VISIBLE NONE;"
            "SimTargetFlag SimTargetFlag "
            "VISIBLE NONE;"
            "Shape_Length Shape_Length "
            "VISIBLE NONE;"
            "Shape_Area Shape_Area "
            "VISIBLE NONE;"
            "buildingID_1 buildingID_1 "
            "VISIBLE NONE;"
            "simulated_building_usage simulated_building_usage "
            "VISIBLE NONE;"
            f"{CompareTypes.change_of_building_usage.name} "
            f"{CompareTypes.change_of_building_usage.name} "
            "VISIBLE NONE;"
            f"{CompareTypes.change_of_building_usage_d.name} "
            f"{CompareTypes.change_of_building_usage_d.name} "
            "VISIBLE NONE;"
            f"{CompareTypes.change_of_building_existence.name} "
            f"{CompareTypes.change_of_building_existence.name} "
            "VISIBLE NONE;"
            "simulated_building_height simulated_building_height "
            "VISIBLE NONE;"
            f"{CompareTypes.change_of_building_height.name} "
            f"{CompareTypes.change_of_building_height.name} "
            "VISIBLE NONE"
        ),
    )
    building_footprnit_layer = arcpy.management.ApplySymbologyFromLayer(
        in_layer=building_footprnit_layer,
        in_symbology_layer=symbol.filepath,
        symbology_fields=symbol.field,
        update_symbology="DEFAULT",
    )
    arcpy.management.SaveToLayerFile(
        in_layer=building_footprnit_layer,
        out_layer=str(output.layer_file),
        is_relative_path=None,
        version="CURRENT",
    )
    logger.info("Complete processing.")
    arcpy.AddMessage("レイヤー ファイル作成完了 (7/8)")


# マップへのレイヤー追加
def add_layer_to_map(output: Output):
    logger = set_log_format("add_layer_to_map")
    logger.info("Start processing.")
    active_project = arcpy.mp.ArcGISProject("CURRENT")
    for map in active_project.listMaps():
        if map.mapType == "SCENE":
            active_map = map
    active_map.addLayer(arcpy.mp.LayerFile(str(output.layer_file)))
    logger.info("Complete processing.")
    arcpy.AddMessage("地図への追加完了 (8/8)")


# 建築物ID更新
def apply_buildingID():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table,
        [
            "objctvtbl_buildingID",
            "sbjctvtbl_buildingID",
            "buildingID",
        ],
    ) as table:
        for rows in table:
            if rows[0] is None and rows[1] is not None:
                rows[2] = rows[1]
                table.updateRow(rows)
            elif rows[0] is not None and rows[1] is None:
                rows[2] = rows[0]
                table.updateRow(rows)
            elif rows[0] is not None and rows[1] is not None:
                rows[2] = rows[1]
                table.updateRow(rows)


def compare_usage(detail: str):
    if detail == UsageChange.UNCHANGED.value:
        return UsageChange.UNCHANGED.value
    if detail == UsageChange.VACANT_TO_RESIDENCE.value:
        return UsageChange.VACANT_TO_RESIDENCE.value
    if detail.startswith("空地→"):
        return UsageChange.VACANT_TO_OTHER.value
    if detail.endswith("→空地"):
        return UsageChange.TO_VACANT.value
    if detail.startswith("住宅→"):
        return UsageChange.RESIDENCE_TO_OTHER.value
    if detail.endswith("→住宅"):
        return UsageChange.OTHER_TO_RESIDENCE.value
    return UsageChange.OTHER_TO_OTHER.value


def compare_usage_detail(obj: Optional[int], sbj: Optional[int]):
    if (
        obj == sbj
        or obj not in VIZ_USAGE_NAMES
        or sbj not in VIZ_USAGE_NAMES
        or VIZ_USAGE_NAMES[obj] == VIZ_USAGE_NAMES[sbj]
    ):
        return UsageChange.UNCHANGED.value
    return f"{VIZ_USAGE_NAMES[obj]}→{VIZ_USAGE_NAMES[sbj]}"


# 建築物用途比較
def set_compared_usage():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table,
        [
            "objctvtbl_Usage",
            "sbjctvtbl_Usage",
            CompareTypes.change_of_building_usage.name,
            CompareTypes.change_of_building_usage_d.name,
        ],
    ) as table:
        for rows in table:
            detail = compare_usage_detail(rows[0], rows[1])
            rows[2] = compare_usage(detail)
            rows[3] = detail
            table.updateRow(rows)


# 建築物存在有無
def classify_existence():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table,
        [
            "objctvtbl_Existing",
            "sbjctvtbl_Existing",
            CompareTypes.change_of_building_existence.name,
        ],
    ) as table:
        for rows in table:
            if rows[0] == 2 and rows[1] == 1:
                rows[2] = "空地に建築物ができる"
                table.updateRow(rows)
            elif rows[0] == 1 and rows[1] == 2:
                rows[2] = "空地になる"
                table.updateRow(rows)
            elif rows[0] == rows[1]:
                rows[2] = "変わらない"
                table.updateRow(rows)


# 建築物高さ | 将来建築物FootPrintの高さは0に設定
def calculate_height():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table, HEIGHT_FIELDS
    ) as table:
        for rows in table:
            if rows[0] is None and rows[1] is None:
                rows[3] = 0
                table.updateRow(rows)
            elif rows[0] is None and rows[1] is not None:
                rows[3] = rows[1]
                table.updateRow(rows)
            elif rows[0] is not None and rows[1] is None:
                rows[3] = -rows[0]
                table.updateRow(rows)
            elif rows[0] is not None and rows[1] is not None:
                rows[3] = rows[1] - rows[0]
                table.updateRow(rows)


# 建築物高さの比較
def compare_height():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table, HEIGHT_FIELDS
    ) as table:
        for rows in table:
            if rows[0] is None and rows[1] is not None:
                rows[2] = rows[1]
                table.updateRow(rows)
            elif rows[0] is not None and rows[1] is None:
                rows[2] = 0
                table.updateRow(rows)
            else:
                rows[2] = rows[1]
                table.updateRow(rows)


# 建築物高さの差分
def classify_height():
    with arcpy.da.UpdateCursor(
        Tables.visualization_working_table, HEIGHT_FIELDS
    ) as table:
        for rows in table:
            if rows[3] < 0:
                rows[4] = "減少"
                table.updateRow(rows)
            elif rows[3] == 0:
                rows[4] = "変化なし"
                table.updateRow(rows)
            elif rows[3] < 10:
                rows[4] = "増加 差分10m未満"
                table.updateRow(rows)
            elif rows[3] >= 10:
                rows[4] = "増加 差分10m以上"
                table.updateRow(rows)


# ログ
def set_log_format(name: str, file_path: str = str(LOG_PATH)):
    logger = logging.getLogger(name)
    logger.disabled = False
    logger.setLevel(logging.INFO)
    if len(logger.handlers) == 0:
        handler = logging.FileHandler(str(file_path))
        handler.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s [%(name)s] - %(levelname)s - %(message)s"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger


if __name__ == "__main__":
    main()
