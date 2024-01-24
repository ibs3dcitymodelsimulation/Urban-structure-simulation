"""
建築物データ作成機能
*2023/10/15 修正
*2023/10/20
    階数計算にて0階になる場合、1階として判定するように修正
    前面道路幅員のバッファを10m→30mに変更
    ゾーンコードを将来建築物に付与
    統合建築物IDを重なる建物全てに付与
    シミュレーション対象フラグを用途に応じて付与
    出力されるBuildingに緯度経度付与
    補間フラグを付与
*2023/10/25: 将来建築物にシミュレーション対象フラグを付与
*2023/10/30
    出力ファイルのデータ型修正
    統合ID付与の方法を建築物重心から重なるへ変更
*2023/11/22
    用途補完にて、建築物の面積2500㎡以上を対象に「999」を付与
    幅員の計算は前面道路幅員のバッファに重心を含む建物から重なる建物を対象とするように変更
"""
import arcpy
import logging
import logging.handlers
import pandas as pd
import numpy as np
import os
import pathlib

# このソースのパス(基準用)
current_dir_path = pathlib.Path(__file__)
# InputDataGenerationディレクトリのパス
input_data_generation_path = str(current_dir_path.parents[1])
# Toolディレクトリパス
tool_dir_path = str(current_dir_path.parents[0])

# 出力用ディレクトリパス
output_dir_path = os.path.join(
    str(current_dir_path.parents[2]), r"Simulation\BaseData")
# 出力用FGDB
output_fgdb = os.path.join(output_dir_path, "BaseData.gdb")
# 建築物データ
building = os.path.join(output_fgdb, "Building")
# 中間FGDB
intermediate_fgdb = os.path.join(tool_dir_path, "Intermediate.gdb")
# 建築物データ(中間)
lod1_building_intermediate = os.path.join(intermediate_fgdb, "lod1_Building")
# 特定地域（DesignatedArea）
designated_area = os.path.join(intermediate_fgdb, "DesignatedArea")
# 統合エリアデータ
integrated_area = os.path.join(intermediate_fgdb, "IntegratedArea")
# 統合FootPrint
integrated_foot_print = os.path.join(intermediate_fgdb, "IntegratedFootPrint")
# 将来建築物FootPrint
bld_foot_print = os.path.join(intermediate_fgdb, "FootPrint")
# 駅データ(出力)
station = os.path.join(intermediate_fgdb, "Station")

# ロガー
global log

log_level = logging.INFO

# log出力先
log_file_path = os.path.join(tool_dir_path, r"Logs\BuildingCreation.log")


def script_tool(
    lod1_building,
    lod1_use_district,
    lod1_land_use,
    zone_polygon,
    road_nw,
    station_location,
    out_coordinate_system
):
    try:
        log = set_log_format("BuildingCreate.py")
        log.info("処理開始")
        # 作業用FGDB作成
        arcpy.management.CreateFileGDB(
            out_folder_path=os.path.dirname(intermediate_fgdb),
            out_name=os.path.basename(intermediate_fgdb))
        # 出力用FGDB作成
        arcpy.management.CreateFileGDB(
            out_folder_path=os.path.dirname(output_fgdb),
            out_name=os.path.basename(output_fgdb))
        # 各ポリゴンの面積や座標の距離を測るため、投影法を統一
        # zone_polygon
        in_coor_system_zone = arcpy.Describe(zone_polygon).spatialReference
        zone_polygon_pro = os.path.join(intermediate_fgdb, "zone_polygon_pro")
        arcpy.management.Project(
            in_dataset=zone_polygon,
            out_dataset=zone_polygon_pro,
            in_coor_system=in_coor_system_zone,
            out_coor_system=out_coordinate_system
        )
        # lod1_building
        in_coor_system_bld = arcpy.Describe(lod1_building).spatialReference
        lod1_building_pro = os.path.join(
            intermediate_fgdb, "lod1_Building_pro")
        arcpy.management.Project(
            in_dataset=lod1_building,
            out_dataset=lod1_building_pro,
            in_coor_system=in_coor_system_bld,
            out_coor_system=out_coordinate_system
        )
        # land_use
        in_coor_system_luse = arcpy.Describe(lod1_land_use).spatialReference
        lod1_land_use_pro = os.path.join(
            intermediate_fgdb, "lod1_land_Use_pro")
        arcpy.management.Project(
            in_dataset=lod1_land_use,
            out_dataset=lod1_land_use_pro,
            in_coor_system=in_coor_system_luse,
            out_coor_system=out_coordinate_system
        )
        # use_district
        in_coor_system_ud = arcpy.Describe(lod1_use_district).spatialReference
        lod1_use_district_pro = os.path.join(
            intermediate_fgdb, "lod1_use_district_pro")
        arcpy.management.Project(
            in_dataset=lod1_use_district,
            out_dataset=lod1_use_district_pro,
            in_coor_system=in_coor_system_ud,
            out_coor_system=out_coordinate_system
        )
        # road_nw
        in_coor_system_nw = arcpy.Describe(road_nw).spatialReference
        road_nw_pro = os.path.join(intermediate_fgdb, "roadNW_pro")
        arcpy.management.Project(
            in_dataset=road_nw,
            out_dataset=road_nw_pro,
            in_coor_system=in_coor_system_nw,
            out_coor_system=out_coordinate_system
        )
        # 欠損値補完
        complement_missing_value(
            zone_polygon_pro,
            lod1_building_pro,
            lod1_land_use_pro)
        # 将来建築物FootPrint作成
        create_future_building_foot_print(
            lod1_use_district_pro,
            lod1_land_use_pro,
            lod1_building_intermediate)
        # 統合FootPrint作成
        create_integrated_foot_print(
            lod1_building_intermediate,
            bld_foot_print,
            designated_area,
            lod1_use_district_pro)
        # 建築物データにFootPrintを統合
        lod1_building_intermediate2 = integrate_building(
            lod1_building_intermediate,
            bld_foot_print,
            integrated_foot_print)
        # 前面道路幅員の付与
        assignment_front_road(
            lod1_building_intermediate2,
            road_nw_pro)
        # アウトプットファイル作成
        create_output_file(
            lod1_building_intermediate2,
            zone_polygon_pro)
        # 最寄り駅情報作成
        create_nearest_station(
            building,
            station_location
        )

    except Exception as e:
        logging_error("例外が発生しました。", e, log)
        arcpy.AddError(e)

    else:
        log.info("正常に処理が終了しました。")


# 欠損値補完
def complement_missing_value(zone_polygon, lod1_building, lod1_land_use):
    log = set_log_format("complementMissingValue()")
    log.info("処理開始")
    # 1)ゾーンコードを付与
    give_zone_code(zone_polygon, lod1_building)
    # 2)建築年の補完テーブルを作成
    construction_year_table = ceate_construction_year_table(lod1_building)
    # 3)用途の補完
    complement_usage(lod1_building, lod1_land_use)
    # 4) 建築年の補完
    complement_year(lod1_building, construction_year_table)
    # 7)建築物の高さを付与
    add_display_high_median(lod1_building)
    # 5) 地上階数の補完
    complement_number_of_ground_floors(lod1_building)
    # 6)延床面積の補間
    complement_total_floor_area(lod1_building)

    log.info("処理終了")


# 将来建築物FootPtint作成
def create_future_building_foot_print(
    lod1_use_district, lod1_land_use, lod1_building
):
    log = set_log_format("createFutureBuildingFootPrint()")
    log.info("処理開始")

    # 商業用地対象エリア_作業用
    business_district_edit = os.path.join(
        intermediate_fgdb, "BusinessDistrict_edit")
    # 住宅用地対象エリア（ResidentialDistrict）
    residential_district = os.path.join(
        intermediate_fgdb, "ResidentialDistrict")

    # 1)FootPrint作成エリアの設定
    set_foot_print_creation_area(
        lod1_building, lod1_use_district, lod1_land_use,
        business_district_edit, residential_district)
    # 2)住宅用将来建築物FootPrintの作成
    housing_foot_print = create_housing_foot_print(
        lod1_building, residential_district)
    # 3)商業用将来建築物FootPrint作成
    business_foot_print = create_business_foot_print(
        business_district_edit, lod1_building,
        lod1_use_district)
    # 4)将来建築物FootPrintの作成
    create_foot_print(business_foot_print, housing_foot_print)

    log.info("処理終了")


# 統合FootPrint作成
def create_integrated_foot_print(
        lod1_building, foot_print,
        designated_area, lod1_use_district):
    log = set_log_format("createIntegratedFootPrint()")
    log.info("処理開始")
    # 統合エリアデータ_外側
    integrated_area_outside_buffer = os.path.join(
        intermediate_fgdb, "IntegratedAreaBufferOutside"
    )
    # 統合エリアデータ_一時
    integrated_area_tmp = os.path.join(intermediate_fgdb, "IntegratedArea_tmp")
    integrated_area_dis = os.path.join(intermediate_fgdb, "IntegratedArea_dis")
    integrated_area_spt = os.path.join(intermediate_fgdb, "IntegratedArea_spt")
    # 土地利用データを再度作成
    in_coordinate_system = arcpy.Describe(lod1_land_use).spatialReference
    lod1_land_use_for_integrated_area = os.path.join(
        intermediate_fgdb, "lod1_land_use_for_integrated_area")
    arcpy.management.Project(
        in_dataset=lod1_land_use,
        out_dataset=lod1_land_use_for_integrated_area,
        in_coor_system=in_coordinate_system,
        out_coor_system=out_coordinate_system
        )
    # 統合FootPrint作成
    # 統合エリアデータ（IntegratedArea）作成
    create_integrated_area(lod1_land_use_for_integrated_area,
        integrated_area_dis, integrated_area_tmp, designated_area)
    # 統合エリアデータ（IntegratedArea）に外側バッファ１ｍを行う
    arcpy.analysis.Buffer(
        in_features=integrated_area_tmp,
        out_feature_class=integrated_area_outside_buffer,
        buffer_distance_or_field="1 Meters",
    )
    arcpy.management.Delete(integrated_area_tmp)
    # 統合エリアデータ（IntegratedArea）に「urf_建蔽率」とIDを付与する
    add_field_integrated_area(integrated_area_outside_buffer, integrated_area_spt, lod1_use_district)
    # 統合エリアデータ（IntegratedArea）の内側バッファを１ｍ毎に実施し、面積を算出し、建蔽率（④で算出した面積/③の初期面積）以下になるまでバッファを行う。
    # バッファ用出力レイヤー1
    integrated_area_inside_buffer1 = os.path.join(
        intermediate_fgdb, "IntegratedAreaInsideBuffer1"
    )
    # バッファ用出力レイヤー2
    integrated_area_inside_buffer2 = os.path.join(
        intermediate_fgdb, "IntegratedAreaInsideBuffer2"
    )
    # 不要なフィールド削除
    arcpy.management.DeleteField(
        in_table=integrated_area_spt, drop_field=["BUFF_DIST", "ORIG_FID"]
    )
    buffer_inside_loop(
        input=integrated_area_spt,
        output=integrated_area_inside_buffer1,
        layer1=integrated_area_inside_buffer1,
        layer2=integrated_area_inside_buffer2,
        res_layer=integrated_area,
    )
    arcpy.management.Delete(integrated_area_spt)
    # 内側バッファ・外側バッファ
    buffer_integrated_area(integrated_area)
    # 統合FootPrint(IntegratedFootPrint)を作成
    # 建築物データ（lod1_Building）にフィールド（IntegratedAreaID）を追加
    add_integrated_area_id_lod1_building(lod1_building, integrated_area)
    # 将来建築物FootPrint(FootPrint)にフィールド（IntegratedAreaID）を追加
    add_integrated_area_id_foot_print(foot_print, integrated_area)
    log.info("処理終了")


# 建築物データにFootPrintを統合
def integrate_building(lod1_building, bld_foot_print, integrated_foot_print):
    log = set_log_format("integrateBuilding()")
    log.info("処理開始")
    # 存在ありなし入力
    arcpy.management.CalculateField(
        in_table=lod1_building,
        field="Existing",
        expression="1",
        field_type="SHORT",
    )
    arcpy.management.CalculateField(
        in_table=integrated_foot_print,
        field="Existing",
        expression="2",
        field_type="SHORT",
    )
    arcpy.management.CalculateField(
        in_table=bld_foot_print,
        field="Existing",
        expression="2",
        field_type="SHORT",
    )
    # 建築物データに将来建築物FootPrint、統合FootPrintを統合する
    # 編集用lod1_Building2
    lod1_building_intermediate2 = os.path.join(
        intermediate_fgdb, "lod1_Building_2")
    arcpy.ddd.MultiPatchFootprint(
        in_feature_class=lod1_building,
        out_feature_class=lod1_building_intermediate2)
    arcpy.management.Append(
        inputs=[integrated_foot_print, bld_foot_print],
        target=lod1_building_intermediate2,
        schema_type="NO_TEST",
        # uro_建築物識別情報_建物ID(uro_buildingIDAttribute_buildingID）、IntegratedAreaId
        field_mapping=f'uro_buildingIDAttribute_buildingID "uro_建築物識別情報_建物ID" \
            true true false 50 Text 0 0,First,#,\
            {integrated_foot_print},\
            uro_buildingIDAttribute_buildingID,0,255,\
            {bld_foot_print},uro_buildingIDAttribute_buildingID,0,\
            255;IntegratedAreaID "IntegratedAreaID" true true false 255 Text \
            0 0,First,#,{bld_foot_print},IntegratedAreaID,0,255;\
            Existing "Existing" true true false 2 Short 0 0,First,#,\
            {integrated_foot_print},Existing,-1,-1,\
            {bld_foot_print},Existing,-1,-1',
    )
    arcpy.management.Delete(bld_foot_print)

    log.info("処理終了")
    return lod1_building_intermediate2


# 前面道路幅員の付与
def assignment_front_road(lod1_building, road_nw):
    log = set_log_format("assignmentFrontRoad()")
    log.info("処理開始")
    # 30mバッファ作成
    road_nw_out = os.path.join(intermediate_fgdb, "road_nw_buf")
    arcpy.analysis.Buffer(
        in_features=road_nw,
        out_feature_class=road_nw_out,
        buffer_distance_or_field="30 Meters",
    )
    # 計算用のwidth_tmp追加
    code_block = """def calcWidth(Separation, width):
    if Separation == 1:
        ans = width * 2
        return ans
    else:
        return width"""
    arcpy.management.CalculateField(
        in_table=road_nw_out,
        field="Width_tmp",
        expression="calcWidth(!Separation!, !Width!)",
        code_block=code_block,
        field_type="LONG",
    )
    # 「前面道路幅員」(dorowidth)の付与
    set_dorowidth(lod1_building, road_nw_out)

    log.info("処理終了")


# アウトプットファイル作成
def create_output_file(lod1_building, zone_polygon):
    log = set_log_format("createOUtputFile()")
    log.info("処理開始")

    # 重心の値付与
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="Lon CENTROID_X;Lat CENTROID_Y",
        length_unit="",
        area_unit="",
        coordinate_system=6668,
        coordinate_format="DD"
    )

    # ゾーンコードの付与のし直し
    set_zone_code_r(zone_polygon, lod1_building)
    # "建築物_現況"作成
    create_building(lod1_building)
    # フィールドの操作
    operate_field()

    log.info("処理終了")


# 最寄り駅情報作成
def create_nearest_station(building_now,
                           station_location):
    log = set_log_format("createNearestStation()")
    log.info("処理開始")
    # 駅データ_編集中
    station_tmp = os.path.join(intermediate_fgdb, "Station_tmp")
    # 最寄り駅情報_一時
    dist_building_station_tmp = os.path.join(
        output_fgdb, "lod1_Building_station_tmp"
    )
    # 最寄り駅情報_出力対象
    dist_building_station = os.path.join(output_fgdb, "Dist_Building_Station")

    # 建築物別最寄り駅距離データ（Dist_Building_Station）の作成
    create_dist_building_station(station_tmp, station_location, building_now,
      dist_building_station_tmp, dist_building_station)
    # 建築物別最寄り駅距離データ（Dist_Building_Station）にフィールド追加
    add_field_dist_building_station(dist_building_station_tmp, dist_building_station)
    # Dist_Building_StationのCSV出力
    output_dist_building_station(dist_building_station, dist_building_station_tmp)
    # BuildingのCSV出力
    output_building_csv(building_now)

    log.info("処理終了")


# ゾーンコードを付与
def give_zone_code(zone_polygon, lod1_building):
    # ゾーンポリゴン(出力)
    zone_polygon_output = os.path.join(output_fgdb, "Zone_Polygon")
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=zone_polygon,
        out_path=os.path.dirname(zone_polygon_output),
        out_name=os.path.basename(zone_polygon_output),
    )

    # 建築物データとゾーンポリゴンが交わった建築物を抽出
    arcpy.management.AddField(lod1_building, "zone_code", "TEXT")
    # ここで作成したCursorが別のカーソルにぶつかってしまうので、zone_codeのlistのみ取得
    zone_code_list = []
    with arcpy.da.SearchCursor(zone_polygon_output, ["zone_code"]) as cur:
        for row in cur:
            zone_code_list.append(row[0])
    # zone_code分繰り返し
    for zone_code in zone_code_list:
        zone_code_str = f"'{zone_code}'"

        zone_polygon_select = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=zone_polygon_output,
            where_clause=f"zone_code = {zone_code_str}",
        )

        lod1_building_select = arcpy.management.SelectLayerByLocation(
            in_layer=lod1_building,
            overlap_type="HAVE_THEIR_CENTER_IN",
            select_features=zone_polygon_select,
        )
        # ゾーンコードを付与
        arcpy.management.CalculateField(
            in_table=lod1_building_select,
            field="zone_code",
            expression=zone_code_str
        )
        arcpy.management.Delete(zone_polygon_select, lod1_building_select)


# 建築年の補完テーブルを作成
def ceate_construction_year_table(lod1_building):
    # 建築年の補完テーブル計算
    construction_year_table = pd.DataFrame(
        index=[],
        columns=[
            "zone_code",
            "bldg_usage1",
            "bldg_yearOfConstruction",
            "numberOfBuilding",
            "ratio",
        ],
    )
    fields = ["zone_code", "bldg_usage1", "bldg_yearOfConstruction"]
    # 処理するためにCursorからタプルに変更
    # ソート
    with arcpy.da.SearchCursor(
        lod1_building,
        fields,
        "bldg_usage1 IS NOT NULL and bldg_yearOfConstruction IS NOT NULL\
        and bldg_usage1 <> '' and bldg_yearOfConstruction <> ''",
    ) as cur:
        # cur = sorted(cur)
        record_list = []
        for row in cur:
            record_list.append(list(row))
    # 建築年の補完テーブル作成
    # 作業用dataframe作成
    df = pd.DataFrame(record_list, columns=fields)
    # 計算用のリスト作成
    usage_list = []
    year_list = []
    # 重複削除
    seen = []
    record_list = [x for x in record_list
                   if x not in seen and not seen.append(x)]
    # レコード分繰り返し(重複は排除)
    for row in record_list:
        building_sql = f"zone_code=='{row[0]}'"
        usage_sql = f"{building_sql} & bldg_usage1=='{row[1]}'"
        year_sql = f"{usage_sql} & bldg_yearOfConstruction=='{row[2]}'"
        # 件数
        building_count = df.query(building_sql).count()[0]
        # 件数10件以上時の処理
        if 10 <= building_count:
            # 同用途数
            usage_count = df.query(usage_sql).count()[0]
            # 同年棟数
            year_count = df.query(year_sql).count()[0]
            # 割合(件数/同用途数)
            ratio = year_count / usage_count
            # 目的のdataframeに追加
            data = pd.Series({
                fields[0]: row[0],
                fields[1]: row[1],
                fields[2]: row[2],
                'numberOfBuilding': year_count,
                'ratio': ratio})
            construction_year_table = construction_year_table.append(
                data, ignore_index=True)

        usage_list.append(row[1])
        year_list.append(row[2])

    usage_list = set(usage_list)
    year_list = set(year_list)

    # 市全域の計算
    for usage in usage_list:
        usage_sql = f"bldg_usage1=='{usage}'"
        usage_count = df.query(usage_sql).count()[0]
        for year in year_list:
            building_sql = f"{usage_sql} & bldg_yearOfConstruction=='{year}'"
            # 同年棟数
            building_count = df.query(building_sql).count()[0]
            # 割合(件数/同用途数)
            ratio = building_count / usage_count
            # 目的のdataframeに追加
            data = pd.Series({
                fields[0]: "指定なし",
                fields[1]: usage,
                fields[2]: year,
                'numberOfBuilding': building_count,
                'ratio': ratio})
            construction_year_table = construction_year_table.append(
                data, ignore_index=True)

    # construction_year_table.to_csv(
    #     os.path.join(output_dir_path, "construction_year_table.csv"), index=False)
    return construction_year_table


# 建築用途の補完
def complement_usage(lod1_building, lod1_land_use):
    # 中間データ
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=lod1_building,
        out_path=os.path.dirname(lod1_building_intermediate),
        out_name=os.path.basename(lod1_building_intermediate),
    )
    # luse_土地利用区分を付与
    arcpy.management.AddField(lod1_building, "luse_class", "TEXT")
    # 補間フラグ作成
    arcpy.management.CalculateField(
            in_table=lod1_building,
            field="ConpletionFlag_Usage",
            expression=0,
            field_type="LONG"
    )
    with arcpy.da.SearchCursor(lod1_land_use, ["luse_class"]) as luse_list:
        luse_list = sorted(luse_list)
        luse_class_tmp = ""
        for row in luse_list:
            if row[0] == luse_class_tmp:
                continue

            luse_class_tmp = row[0]
            lod1_land_use_select = arcpy.management.SelectLayerByAttribute(
                in_layer_or_view=lod1_land_use,
                where_clause=f"luse_class = '{row[0]}'"
            )
            # 空間検索
            lod1_building_select = arcpy.management.SelectLayerByLocation(
                in_layer=lod1_building,
                overlap_type="HAVE_THEIR_CENTER_IN",
                select_features=lod1_land_use_select,
            )
            # luse_土地利用区分付与
            arcpy.management.CalculateField(
                in_table=lod1_building_select,
                field="luse_class",
                expression=f"'{row[0]}'"
            )
            arcpy.management.Delete(
                [lod1_building_select, lod1_land_use_select]
            )
    # 建物用途補間割合.csv
    building_usage_table_csv = os.path.join(
        input_data_generation_path, r"Input\建物用途補間割合.csv")
    # 建物用途補完割合.csv読込
    building_usage_table = pd.read_csv(
        building_usage_table_csv, encoding="shift-jis")
    # 建築物の面積2500㎡以上を対象の用途に「999」を付与
    set_usage_999(lod1_building)
    # 建築物データのbldg_用途1の空欄を対象に補完
    lod1_building_select = arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lod1_building,
        where_clause="bldg_usage1 = '' or bldg_usage1 IS NULL"
    )
    # 建物用途補完
    with arcpy.da.UpdateCursor(
        lod1_building_select,
        ["bldg_usage1", "luse_class", "bldg_measuredHeight",
         "ConpletionFlag_Usage"]
            ) as target_list:
        for target in target_list:
            # 高さ割り当て
            height_class = 0
            luse_class = target[2]
            if target[2] == '211':
                if target[1] is None:
                    luse_class = '-'
                elif target[1] < 5:
                    height_class = 1
                elif 5 <= target[1] < 10:
                    height_class = 2
                elif 10 <= target[1] < 15:
                    height_class = 3
                elif 15 <= target[1]:
                    height_class = 4
            elif target[2] == '212':
                if target[1] is None:
                    luse_class = '-'
                elif target[1] < 5:
                    height_class = 1
                elif 5 <= target[1] < 10:
                    height_class = 2
                elif 10 <= target[1] < 20:
                    height_class = 3
                elif 20 <= target[1] < 30:
                    height_class = 4
                elif 30 <= target[1]:
                    height_class = 5
            elif target[2] not in ['201', '202', '205', '213', '214', '216']:
                luse_class = '-'

            # 該当の割合抽出
            df = building_usage_table[(building_usage_table["高さ_区分"]
                                       == height_class) &
                                      (building_usage_table["土地利用区分_コード"]
                                       == luse_class)]
            ratin = df.loc[:, ['割合']]['割合'].to_list()
            # 割合の合計値が1じゃない場合、再計算
            sum_ratin = sum(ratin)
            # 抽出した割合の合計値が1出ない場合は、1になるように再計算
            if sum_ratin != 1:
                re_ratin = []
                for i in ratin:
                    re_ratin.append(i / sum_ratin)
                ratin = re_ratin
            usage = df.loc[:, ['建物用途_コード']]['建物用途_コード'].to_list()

            target[0] = np.random.choice(usage, p=ratin)
            # 補間フラグを立てる
            target[3] = 1
            target_list.updateRow(target)
    arcpy.management.Delete(lod1_building_select)


# 建築年の補完
def complement_year(lod1_building, construction_year_table):
    lod1_building_select = arcpy.management.SelectLayerByAttribute(
        lod1_building,
        "NEW_SELECTION",
        "bldg_yearOfConstruction = '' or bldg_yearOfConstruction IS NULL"
    )
    # 補間フラグ作成
    arcpy.management.CalculateField(
            in_table=lod1_building,
            field="ConpletionFlag_Age",
            expression=0,
            field_type="LONG"
    )
    # 空欄を取り除く
    with arcpy.da.UpdateCursor(
        lod1_building_select,
        ["zone_code", "bldg_usage1", "bldg_yearOfConstruction",
         "ConpletionFlag_Age"],
        "bldg_yearOfConstruction = '' or bldg_yearOfConstruction IS NULL",
    ) as cur:
        for row in cur:
            zone_code = ""
            # zone_codeが該当するものが存在する場合
            if row[0] in construction_year_table["zone_code"].to_list():
                zone_code = row[0]
            # zone_codeが該当するものが存在しない場合
            else:
                zone_code = "指定なし"
            df_edit = construction_year_table[(
                (construction_year_table["zone_code"].isin(
                    [str(zone_code)]
                    )) &
                (construction_year_table["bldg_usage1"].isin(
                    [str(row[1])]
                    ))
            )]
            # 対象のdataを取得できなかった時、zone_codeを指定なしで検索
            if df_edit.empty:
                df_edit = construction_year_table[
                    construction_year_table["zone_code"].isin(["指定なし"])
                ]
            ratio_list = df_edit.loc[:, "ratio"].to_list()
            sum_ratin = sum(ratio_list)
            if sum_ratin != 1:
                re_ratin = []
                for i in ratio_list:
                    re_ratin.append(i / sum_ratin)
                ratio_list = re_ratin
            year_list = df_edit.loc[:, "bldg_yearOfConstruction"].to_list()
            row[2] = np.random.choice(year_list, p=ratio_list)
            # 補間フラグを立てる
            row[3] = 1
            cur.updateRow(row)
    arcpy.management.Delete(lod1_building_select)


# 地上階数の補完する
def complement_number_of_ground_floors(lod1_building):
    lod1_building_select = arcpy.management.SelectLayerByAttribute(
        lod1_building,
        "NEW_SELECTION",
        "bldg_storeysAboveGround IS NULL"
    )
    # 補間フラグ作成
    arcpy.management.CalculateField(
            in_table=lod1_building,
            field="ConpletionFlag_Storeys",
            expression=0,
            field_type="LONG"
    )
    with arcpy.da.UpdateCursor(
        lod1_building_select,
        ["bldg_storeysAboveGround", "bldg_usage1", "display_high_median",
         "ConpletionFlag_Storeys"]
            ) as target_list:
        # 地上階数.csv
        number_of_floors_csv = os.path.join(
            input_data_generation_path, r"Input\地上階数.csv"
        )
        # 地上階数.csv読込
        number_of_floors = pd.read_csv(
            number_of_floors_csv, encoding="shift-jis"
        )
        for target in target_list:
            df = number_of_floors[
                (number_of_floors["建物用途_コード"] == int(target[1]))]
            if df.empty:
                df = number_of_floors[(number_of_floors["建物用途_コード"].isnull())]
            h = float(target[2])
            k = df.iat[0, 3]
            c1 = df.iat[0, 2]
            n = h / k - c1 / k + 1
            target[0] = n
            # 0階の場合は1階で補間
            if target[0] < 1:
                target[0] = 1
            # 補間フラグを立てる
            target[3] = 1
            target_list.updateRow(target)
    arcpy.management.Delete([lod1_building_select])


# 延床面積の補間
def complement_total_floor_area(lod1_building):
    # 補間フラグ作成
    arcpy.management.CalculateField(
            in_table=lod1_building,
            field="ConpletionFlag_FloorArea",
            expression=0,
            field_type="LONG"
    )
    # 延床面積の補間
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="area AREA",
        area_unit="SQUARE_METERS")
    lod1_building_select = arcpy.management.SelectLayerByAttribute(
        lod1_building,
        "NEW_SELECTION",
        "uro_BuildingDetailAttribute_totalFloorArea IS NULL"
    )
    with arcpy.da.UpdateCursor(
        lod1_building_select,
        ["uro_BuildingDetailAttribute_totalFloorArea",
         "bldg_usage1",
         "bldg_storeysAboveGround",
         "uro_BuildingDetailAttribute_buildingRoofEdgeArea",
         "area",
         "ConpletionFlag_FloorArea"]
         ) as target_list:
        # 延床面積補間パラメータ.csv
        floor_area_csv = os.path.join(
            input_data_generation_path, r"Input\延床面積補間パラメータ.csv")
        # 延床面積補間パラメータ.csvの読み込み
        floor_area = pd.read_csv(floor_area_csv, encoding="shift-jis")
        for target in target_list:
            df = floor_area[(floor_area["建物用途_コード"] == int(target[1]))]
            if df.empty:
                df = floor_area[(floor_area["建物用途_コード"].isnull())]

            if target[3] is None:
                s = target[4]
            else:
                s = target[3]
            n = target[2]
            a = df.iat[0, 2]
            b = df.iat[0, 3]
            r_s = a * (s * (n - 1)) + b * s
            target[0] = r_s
            # 補間フラグを立てる
            target[5] = 1
            target_list.updateRow(target)
    arcpy.management.Delete(lod1_building_select)
    arcpy.management.DeleteField(lod1_building, "area", "DELETE_FIELDS")
    # 中間の建築物データ作成上書き
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=lod1_building,
        out_path=os.path.dirname(lod1_building_intermediate),
        out_name=os.path.basename(lod1_building_intermediate),
    )


# 建築物の高さ付与
def add_display_high_median(lod1_building):
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="z_max EXTENT_MAX_Z"
    )
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="z_min EXTENT_MIN_Z"
    )
    arcpy.management.CalculateField(
        in_table=lod1_building,
        field="display_high_median",
        expression="!z_max! - !z_min!"
    )
    arcpy.management.DeleteField(
        in_table=lod1_building, drop_field=["z_max", "z_min"]
    )


# FootPrint作成エリアを設定する
def set_foot_print_creation_area(
        lod1_building, lod1_use_district, lod1_land_use,
        business_district_edit, residential_district):
    # 特定地域(DesignatedArea)作成
    create_designated_area(lod1_use_district)
    # 土地利用データ（lod1_LandUse）の属性項目「luse_土地利用区分」の222「その他の空地③（平面駐車場）」を抽出し、特定地域（DesignatedArea）に重なる場合と重ならない場合にインターセクトで区分する。
    layer = arcpy.management.SelectLayerByAttribute(
        lod1_land_use,
        "NEW_SELECTION",
        "luse_class = '222'"
    )
    lod1_land_use_designated = os.path.join(
        intermediate_fgdb, "lod1_land_Use_designated")
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=layer,
        out_path=os.path.dirname(lod1_land_use_designated),
        out_name=os.path.basename(lod1_land_use_designated)
    )
    # 住宅用地対象エリア（ResidentialDistrict）作成
    create_residential_district(residential_district, lod1_land_use_designated)
    # 商業用地対象エリア（BusinessDistrict）作成
    create_business_district(business_district_edit, lod1_land_use_designated, lod1_building)


# 住宅用将来建築物FootPtint作成
def create_housing_foot_print(
        lod1_building, residential_district):
    # 住宅用将来建築物FootPrint（HousingFootPrint）
    housing_foot_print = os.path.join(intermediate_fgdb, "HousingFootPrint")

    # 住宅用地対象エリア_テッセレーション用（ResidentialDistrict_tesse）
    residential_district_tesse = os.path.join(
        intermediate_fgdb, "ResidentialDistrict_tesse"
    )
    # 住宅用地対象エリアの重ならないポリゴンを削除する
    delete_outside_area(residential_district_tesse, residential_district)
    # 各ポリゴンの頂点を出力
    residential_footprint_points = extraction_coordinates(residential_district_tesse)
    # residential_footprint_points に建築物ごとにユニークな値を付与
    give_unique_value(residential_district_tesse, residential_footprint_points)
    # 将来建築物フットプリント (住宅) 作成
    housing_foot_print = arcpy.management.MinimumBoundingGeometry(
        in_features=os.path.join(
            intermediate_fgdb,
            "residential_footprint_points_grid_id"
        ),
        out_feature_class=os.path.join(
            intermediate_fgdb, "housing_footprint"
        ),
        geometry_type="ENVELOPE",
        group_option="LIST",
        group_field=["GRID_ID"],
        mbg_fields_option="NO_MBG_FIELDS"
    )
    # 不要のレイヤー削除
    arcpy.management.Delete(residential_district_tesse)
    # 不要なエリアを削除
    delete_unnecessary_area(housing_foot_print, residential_district, lod1_building)

    return housing_foot_print


# 商業用将来建築物FootPrint作成
def create_business_foot_print(
        business_district_edit, lod1_building,
        lod1_use_district):
    # 商業用地対象エリア（BusinessDistrict）
    business_district = os.path.join(intermediate_fgdb, "BusinessDistrict")
    # 用途地域（lod1_UseDistrict）の属性項目「urf_建蔽率」を商業用地対象エリア(BusinessDistrict)に属性として付与する。
    add_building_coverage_rate(business_district_edit, lod1_use_district, business_district)
    # 初期面積割り出し
    arcpy.management.CalculateGeometryAttributes(
        in_features=business_district,
        geometry_property="area_first AREA",
        area_unit="SQUARE_METERS",
    )
    # 商業用将来建築物FootPrint
    business_foot_print1 = os.path.join(
        intermediate_fgdb, "BusinessFootPrint1")
    # バッファ用出力レイヤー1
    business_district_inside_buffer1 = os.path.join(
        intermediate_fgdb, "BusinessDistrictBufferIn1"
    )
    # バッファ用出力レイヤー1
    business_district_inside_buffer2 = os.path.join(
        intermediate_fgdb, "BusinessDistrictBufferIn2"
    )
    # 商業用地対象エリア（BusinessDistrict）の内側バッファを１ｍ毎に実施し、面積を算出し、用途地域の建蔽率（バッファ後の面積/初期面積）以下になるまでバッファを行う。
    buffer_inside_loop(
        input=business_district,
        output=business_district_inside_buffer1,
        layer1=business_district_inside_buffer1,
        layer2=business_district_inside_buffer2,
        res_layer=business_foot_print1,
    )
    # 対象レイヤーから40㎡未満のポリゴンを削除する
    delete_business_foot_print_under_40(business_foot_print1, lod1_building)
    # 商業用将来建築物を整理する
    sort_out_business_foot_print(business_foot_print1, lod1_building)
    # 商業用将来建築物FootPrint(BusinessFootPrint)の作成
    return simplify_business_foot_print(business_foot_print1)


# 将来建築物FootPrint作成
def create_foot_print(business_foot_print, housing_foot_print):
    # 住宅用将来建築物FootPrint（HousingFootPrint）と商業用将来建築物FootPrint(BusinessFootPrint)をマージ
    arcpy.management.Merge(
        inputs=[business_foot_print, housing_foot_print],
        output=bld_foot_print,
        field_mappings=f'Shape_Area "Shape_Area" false true true 8 Double 0 0,\
            First,#,{housing_foot_print},Shape_Area,-1,-1,\
            {business_foot_print},Shape_Area,-1,-1'
    )
    # uro_建築物識別情報_建物ID(uro_buildingIDAttribute_buildingID）を追加し、ＩＤを付与する。
    arcpy.management.AddField(
        in_table=bld_foot_print,
        field_name="uro_buildingIDAttribute_buildingID",
        field_type="TEXT",
    )
    with arcpy.da.UpdateCursor(
        bld_foot_print, ["uro_buildingIDAttribute_buildingID"]
            ) as cur:
        counter = 1
        for row in cur:
            id = f"FP{str(counter).rjust(7, '0')}"
            row[0] = id
            cur.updateRow(row)
            counter += 1


# 特定地域(DesignatedArea)作成
def create_designated_area(lod1_use_district):
    lod1_use_district_select = arcpy.management.SelectLayerByAttribute(
        lod1_use_district,
        "NEW_SELECTION",
        "urf_function = '9' or urf_function = '10'"
    )
    arcpy.management.Dissolve(
        in_features=lod1_use_district_select,
        out_feature_class=designated_area,
        multi_part="SINGLE_PART",
    )
    arcpy.management.Delete(lod1_use_district_select)


# 住宅用地対象エリア（ResidentialDistrict）作成
def create_residential_district(residential_district, lod1_land_use_designated):
    # 特定地域外
    designated_area_out = arcpy.management.SelectLayerByLocation(
        in_layer=lod1_land_use_designated,
        select_features=designated_area,
        invert_spatial_relationship="INVERT",
    )
    # 住宅用地対象エリア（ResidentialDistrict）作成
    # 土地利用データ（lod1_LandUse）の属性項目「luse_土地利用区分」の「住宅用地（住宅、共同住宅、店舗等併用住宅、店舗等併用共同住宅、作業所併用住宅）」取得
    lod1_land_use_select = arcpy.management.SelectLayerByAttribute(
        lod1_land_use,
        "NEW_SELECTION",
        "luse_class = '211'"
    )
    # マージ
    residential_district_merge = os.path.join(
        intermediate_fgdb, "ResidentialDistrict_Merge")
    arcpy.management.Merge(
        inputs=[designated_area_out, lod1_land_use_select],
        output=residential_district_merge,
    )
    # ディゾルブ
    arcpy.management.Dissolve(
        in_features=residential_district_merge,
        out_feature_class=residential_district,
        multi_part="SINGLE_PART",
    )
    arcpy.management.Delete(
        [residential_district_merge, designated_area_out,
         lod1_land_use_select])


# 商業用地対象エリア（BusinessDistrict）作成
def create_business_district(business_district_edit,
        lod1_land_use_designated, lod1_building):
    # 商業用地ポリゴンを抽出
    lod1_land_use_select = arcpy.management.SelectLayerByAttribute(
        lod1_land_use,
        "NEW_SELECTION",
        "luse_class = '212'"
    )
    # 「商業用地」のポリゴンのうち、建築物データ（lod1_Building）と重複するポリゴンは削除する。
    lod1_LandUse_delete = arcpy.management.SelectLayerByLocation(
        in_layer=lod1_land_use_select,
        select_features=lod1_building,
        selection_type="SUBSET_SELECTION",
        invert_spatial_relationship="NOT_INVERT"
    )
    arcpy.management.DeleteRows(lod1_LandUse_delete)
    # 特定地域と編集した商業ポリゴンをマージ・ディゾルブ・シングルパート
    # 特定地域（DesignatedArea_merge）
    designated_area_merge = os.path.join(
        intermediate_fgdb, "DesignatedArea_merge"
    )
    # 特定地域内
    designated_area_in = arcpy.management.SelectLayerByLocation(
        in_layer=lod1_land_use_designated,
        select_features=designated_area,
        invert_spatial_relationship="NOT_INVERT",
    )
    # 商業用地ポリゴンを抽出
    lod1_land_use_select = arcpy.management.SelectLayerByAttribute(
        lod1_land_use,
        "NEW_SELECTION",
        "luse_class = '212'"
    )
    arcpy.management.Merge(
        inputs=[designated_area_in, lod1_land_use_select],
        output=designated_area_merge,
    )
    arcpy.management.Dissolve(
        in_features=designated_area_merge,
        out_feature_class=business_district_edit,
        multi_part="SINGLE_PART",
    )
    # 7000以上100未満ポリゴン削除
    arcpy.management.CalculateGeometryAttributes(
        in_features=business_district_edit,
        geometry_property="area AREA",
        area_unit="SQUARE_METERS",
    )
    business_district_edit_delete = arcpy.management.SelectLayerByAttribute(
        business_district_edit,
        "NEW_SELECTION",
        "area >= 7000 or area < 100"
    )
    arcpy.management.DeleteRows(business_district_edit_delete)
    arcpy.management.Delete(
        [designated_area_merge, lod1_LandUse_delete, lod1_land_use_select,
         designated_area_in, business_district_edit_delete,
         lod1_land_use_designated])


# 住宅用地対象エリアの重ならないポリゴンを削除する
def delete_outside_area(residential_district_tesse, residential_district):
    # 住宅用ポリゴンを配置する
    out_sr = arcpy.SpatialReference()
    out_sr.loadFromString(out_coordinate_system)
    arcpy.management.GenerateTessellation(
        Output_Feature_Class=residential_district_tesse,
        Extent=residential_district,
        Shape_Type="SQUARE",
        Size="169 SquareMeters",
        Spatial_Reference=out_sr.factoryCode
    )
    # 不要な部分を削除
    residential_district_tesse_delete = arcpy.management.SelectLayerByLocation(
        in_layer=residential_district_tesse,
        overlap_type="COMPLETELY_WITHIN",
        select_features=residential_district,
        invert_spatial_relationship="INVERT",
    )
    arcpy.management.DeleteRows(residential_district_tesse_delete)


# ポリゴンの各頂点を抽出
def extraction_coordinates(residential_district_tesse, ):
    # 各ポリゴンの頂点を出力
    arcpy.management.CalculateGeometryAttributes(
        in_features=residential_district_tesse,
        geometry_property=[
            ["EXTENT_MIN_X", "EXTENT_MIN_X"],
            ["EXTENT_MIN_Y", "EXTENT_MIN_Y"],
            ["EXTENT_MAX_X", "EXTENT_MAX_X"],
            ["EXTENT_MAX_Y", "EXTENT_MAX_Y"],
        ],
        length_unit="METERS",
    )
    # テーブルに建築物フットプリントの四隅の座標を書き込む
    future_residents_footprint_table = arcpy.management.CreateTable(
        out_path=intermediate_fgdb,
        out_name="future_redidents_footprint_table"
    )
    arcpy.management.AddFields(
        in_table=future_residents_footprint_table,
        field_description=[
            ["POINT_X", "DOUBLE"],
            ["POINT_Y", "DOUBLE"]
        ]
    )
    with arcpy.da.SearchCursor(
        residential_district_tesse,
        [
            "EXTENT_MIN_X",
            "EXTENT_MIN_Y",
            "EXTENT_MAX_X",
            "EXTENT_MAX_Y",
        ]
    ) as search_cursor:
        for row in search_cursor:
            # 建物ポリゴンの各頂点を計算
            x_min = row[0] + 1
            y_min = row[1] + 4
            x_max = row[2] - 1
            y_max = row[3] - 1
            xmin_ymin = (x_min, y_min)
            xmin_ymax = (x_min, y_max)
            xmax_ymax = (x_max, y_max)
            xmax_ymin = (x_max, y_min)
            with arcpy.da.InsertCursor(
                future_residents_footprint_table,
                [
                    "POINT_X",
                    "POINT_Y"
                ]
            ) as insert_cursor:
                insert_cursor.insertRow(xmin_ymin)
                insert_cursor.insertRow(xmin_ymax)
                insert_cursor.insertRow(xmax_ymax)
                insert_cursor.insertRow(xmax_ymin)
    # 将来建築物フットプリントの四隅のポイント (住宅) (residential_footprint_points)
    out_sr = arcpy.SpatialReference()
    out_sr.loadFromString(out_coordinate_system)
    residential_footprint_points = arcpy.management.XYTableToPoint(
        in_table=future_residents_footprint_table,
        out_feature_class=os.path.join(
            intermediate_fgdb,
            "residential_footprint_points"
        ),
        x_field="POINT_X",
        y_field="POINT_Y",
        coordinate_system=out_sr.factoryCode
    )
    
    return residential_footprint_points


# residential_footprint_points に建築物ごとにユニークな値を付与
def give_unique_value(residential_district_tesse, residential_footprint_points):
    # residential_footprint_points に建築物ごとにユニークな値を付与
    field_mappings = arcpy.FieldMappings()
    field_map = arcpy.FieldMap()
    field_map.addInputField(
        residential_district_tesse,
        "GRID_ID"
    )
    field_mappings.addFieldMap(field_map)
    arcpy.analysis.SpatialJoin(
        target_features=residential_footprint_points,
        join_features=residential_district_tesse,
        out_feature_class=os.path.join(
            intermediate_fgdb,
            "residential_footprint_points_grid_id"
        ),
        field_mapping=field_mappings,
        match_option="COMPLETELY_WITHIN",
    )


# 不要なエリアを削除する
def delete_unnecessary_area(housing_foot_print, residential_district, lod1_building):
    # residential_districtエリア外のフィーチャを削除
    arcpy.management.SelectLayerByLocation(
        in_layer=housing_foot_print,
        overlap_type="COMPLETELY_CONTAINS",
        select_features=residential_district,
        selection_type="NEW_SELECTION",
        invert_spatial_relationship="INVERT",
    )
    # 既存の建物周辺(1m)のフィーチャを削除
    housing_foot_print_delete = arcpy.management.SelectLayerByLocation(
        in_layer=housing_foot_print,
        overlap_type="INTERSECT",
        select_features=lod1_building,
        search_distance="1 Meters",
        selection_type="ADD_TO_SELECTION",
    )
    arcpy.management.DeleteRows(housing_foot_print_delete)


# 「urf_建蔽率」を付与
def add_building_coverage_rate(business_district_edit, lod1_use_district, business_district):
    # 用途地域（lod1_UseDistrict）の属性項目「urf_建蔽率」を商業用地対象エリア(BusinessDistrict)に属性として付与する。
    arcpy.analysis.SpatialJoin(
        target_features=business_district_edit,
        join_features=lod1_use_district,
        out_feature_class=business_district,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping='urf_buildingCoverageRate "urf_建蔽率" true true false 8\
            Double 0 0,First,#,lod1_用途地域,urf_buildingCoverageRate,-1,-1',
        match_option="HAVE_THEIR_CENTER_IN"
    )
    arcpy.management.Delete(business_district_edit)


# 対象レイヤーから40㎡未満のポリゴンを削除する
def delete_business_foot_print_under_40(business_foot_print1, lod1_building):
    # 商業用将来建築物FootPrint(BusinessFootPrint1)の面積が40㎡未満の場合は削除する。
    del_target1 = arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=business_foot_print1,
        selection_type="NEW_SELECTION",
        where_clause="area_calc < 40",
    )
    arcpy.management.DeleteRows(del_target1)
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="area AREA",
        area_unit="SQUARE_METERS",
    )
    # 既存の建築物データ（lod1_Building）の面積が40㎡未満の場合は削除する。
    del_target2 = arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=lod1_building,
        selection_type="NEW_SELECTION",
        where_clause="area < 40",
    )
    arcpy.management.DeleteRows(del_target2)


# 商業用将来建築物のデータの整理
def sort_out_business_foot_print(business_foot_print1, lod1_building):
    # 既存建築物データ（lod1_Building）と商業用将来建築物FootPrint(BusinessFootPrint1)が重複する建物を抽出する。
    target_layer = arcpy.management.SelectLayerByLocation(
        in_layer=business_foot_print1,
        select_features=lod1_building,
    )
    # 商業用将来建築物FootPrintの内側バッファ（2ｍ）(BusinessFootPrint_i)
    business_foot_print_i = os.path.join(
        intermediate_fgdb, "BusinessFootPrint_i"
    )
    arcpy.analysis.Buffer(
        in_features=target_layer,
        out_feature_class=business_foot_print_i,
        buffer_distance_or_field="-2 Meters",
    )
    # 重複している場合は将来建築物FootPrint(BusinessFootPrint1)から削除(重複していない場合も差し替え時削除するので、対象は一旦すべて削除)
    arcpy.management.DeleteRows(target_layer)

    # 重複していない場合は単純化して、商業用将来建築物FootPrint(BusinessFootPrint1)に差し替える。
    layer, layers, count = arcpy.management.SelectLayerByLocation(
        in_layer=business_foot_print_i,
        select_features=lod1_building,
        overlap_type="INTERSECT",
        invert_spatial_relationship="INVERT",
    )
    if int(count) > 0:
        arcpy.management.Append(
            inputs=layer,
            target=business_foot_print1,
            schema_type="NO_TEST"
        )
    arcpy.management.Delete(business_foot_print_i)


# 商業用将来建築物FootPrintの単純化
def simplify_business_foot_print(business_foot_print1):
    business_foot_print = os.path.join(intermediate_fgdb, "BusinessFootPrint")
    business_foot_print_inside = os.path.join(
        intermediate_fgdb, "BusinessFootPrint_in"
    )
    business_foot_print = os.path.join(
        intermediate_fgdb, "BusinessFootPrint_out"
    )
    # 内側バッファ
    arcpy.analysis.Buffer(
        in_features=business_foot_print1,
        out_feature_class=business_foot_print_inside,
        buffer_distance_or_field="-1 Meters",
    )
    arcpy.management.Delete(business_foot_print1)
    # 外側バッファ
    arcpy.analysis.Buffer(
        in_features=business_foot_print_inside,
        out_feature_class=business_foot_print,
        buffer_distance_or_field="1 Meters",
    )
    arcpy.management.Delete(business_foot_print_inside)

    return business_foot_print


# 統合エリアデータ（IntegratedArea）を作成する
def create_integrated_area(lod1_land_use_for_integrated_area,
        integrated_area_dis, integrated_area_tmp, designated_area):
    # 属性検索
    targetRecords = arcpy.management.SelectLayerByAttribute(
        lod1_land_use_for_integrated_area,
        "NEW_SELECTION",
        "luse_class = '211' or luse_class = '212' or luse_class = '213' \
        or luse_class = '219' or luse_class = '222'"
    )
    # ディソルブ・シンプルパート
    arcpy.management.Dissolve(
        in_features=targetRecords,
        out_feature_class=integrated_area_dis,
        dissolve_field="luse_class",
        multi_part="SINGLE_PART",
    )
    arcpy.management.Delete(targetRecords)
    # 統合エリアデータ（IntegratedArea）の初期面積をジオメトリ演算で算出する
    arcpy.management.CalculateGeometryAttributes(
        in_features=integrated_area_dis,
        geometry_property="area_first AREA",
    )
    # designated_areaと重なるエリア抽出
    integrated_area_select = arcpy.management.SelectLayerByLocation(
        in_layer=integrated_area_dis,
        select_features=designated_area,
        invert_spatial_relationship="NOT_INVERT",
    )
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=integrated_area_select,
        out_path=os.path.dirname(integrated_area_tmp),
        out_name=os.path.basename(integrated_area_tmp)
    )
    arcpy.management.Delete([integrated_area_select, integrated_area_dis])
    # 200㎡以下のレコード削除
    targetRecords = arcpy.management.SelectLayerByAttribute(
        integrated_area_tmp,
        "NEW_SELECTION",
        "area_first <= 200"
    )
    arcpy.management.DeleteRows(targetRecords)


def add_field_integrated_area(integrated_area_outside_buffer, integrated_area_spt, lod1_use_district):
    # 用途地域（lod1_UseDistrict）の属性項目「urf_建蔽率」を統合エリアデータ（IntegratedArea）に属性(urf_建蔽率)として付与する
    arcpy.analysis.SpatialJoin(
        target_features=integrated_area_outside_buffer,
        join_features=lod1_use_district,
        out_feature_class=integrated_area_spt,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        field_mapping=f'luse_class "luse_土地利用区分" true true false 10 \
            Text 0 0,First,#,{integrated_area_outside_buffer},\
            luse_class,0,10;area_first "area_first" true true false 8 \
            Double 0 0,First,#,{integrated_area_outside_buffer},\
            area_first,-1,-1;BUFF_DIST "BUFF_DIST" true true false 8 \
            Double 0 0,First,#,{integrated_area_outside_buffer},\
            BUFF_DIST,-1,-1;ORIG_FID "ORIG_FID" true true false 4 Long 0 0,\
            First,#,{integrated_area_outside_buffer},ORIG_FID,-1,-1;\
            Shape_Length "Shape_Length" false true true 8 Double 0 0,First,#,\
            {integrated_area_outside_buffer},Shape_Length,-1,-1;\
            Shape_Area "Shape_Area" false true true 8 Double 0 0,First,#,\
            {integrated_area_outside_buffer},Shape_Area,-1,-1;\
            urf_buildingCoverageRate "urf_建蔽率" true true false 8 Double 0 0,\
            First,#,lod1_用途地域,urf_buildingCoverageRate,-1,-1',
        match_option="HAVE_THEIR_CENTER_IN",
        search_radius=None,
        distance_field_name="",
    )
    arcpy.management.Delete(integrated_area_outside_buffer)
    # 統合エリアデータ（IntegratedArea）にuro_建築物識別情報_建物ID(uro_buildingIDAttribute_buildingID）を追加し、ＩＤを付与する。IFP0000001から順番に付与する。
    arcpy.management.AddField(
        in_table=integrated_area_spt,
        field_name="uro_buildingIDAttribute_buildingID",
        field_type="TEXT",
    )
    with arcpy.da.UpdateCursor(
        integrated_area_spt, ["uro_buildingIDAttribute_buildingID"]
    ) as cur:
        counter = 1
        for row in cur:
            id = f"IFP{str(counter).rjust(7, '0')}"
            row[0] = id
            cur.updateRow(row)
            counter += 1


# 統合エリアデータ（IntegratedArea）にバッファーを掛けて、統合FootPrint（IntegratedFootPrint）の元データを作成する
def buffer_integrated_area(integrated_area):
    # 統合エリアデータ_in
    integrated_area_in = os.path.join(
        intermediate_fgdb, "IntegratedAreaIn"
    )
    # 統合エリアデータ_out
    integrated_area_out = os.path.join(
        intermediate_fgdb, "IntegratedAreaOut"
    )
    # 内側バッファ
    arcpy.analysis.Buffer(
        in_features=integrated_area,
        out_feature_class=integrated_area_in,
        buffer_distance_or_field="-1 Meters",
    )
    # 外側バッファ
    arcpy.analysis.Buffer(
        in_features=integrated_area,
        out_feature_class=integrated_foot_print,
        buffer_distance_or_field="1 Meters",
    )
    arcpy.management.Delete(integrated_area_in)
    arcpy.management.Delete(integrated_area_out)


# 建築物データ（lod1_Building）にフィールド（IntegratedAreaID）を追加
def add_integrated_area_id_lod1_building(lod1_building, integrated_area):
    lod1_building_tmp1 = os.path.join(intermediate_fgdb, "lod1_Building_tmp1")
    lod1_building_tmp2 = os.path.join(intermediate_fgdb, "lod1_Building_tmp2")
    arcpy.ddd.MultiPatchFootprint(
        in_feature_class=lod1_building,
        out_feature_class=lod1_building_tmp1,
    )
    arcpy.analysis.SpatialJoin(
        target_features=lod1_building_tmp1,
        join_features=integrated_area,
        out_feature_class=lod1_building_tmp2,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        # 統合エリアデータ（IntegratedArea）のuro_建築物識別情報_建物ID(uro_buildingIDAttribute_buildingID）の値を付与する。
        field_mapping=f'bldg_usage1 "bldg_用途1" true true false 10 Text 0 0,\
        First,#,{lod1_building_tmp1},bldg_usage1,0,10;\
        bldg_yearOfConstruction "bldg_建築年" true true false 10 Text 0 0,\
        First,#,{lod1_building_tmp1},bldg_yearOfConstruction,0,10;\
        bldg_storeysAboveGround "bldg_地上階数" true true false 4 Long 0 0,\
        First,#,{lod1_building_tmp1},bldg_storeysAboveGround,-1,-1;\
        uro_buildingIDAttribute_buildingID "uro_建築物識別情報_建物ID" true true \
        false 50 Text 0 0,First,#,{lod1_building_tmp1},\
        uro_buildingIDAttribute_buildingID,0,50;\
        uro_BuildingDetailAttribute_totalFloorArea "uro_建物利用現況_延床面積" true \
        true false 8 Double 0 0,First,#,{lod1_building_tmp1},\
        uro_BuildingDetailAttribute_totalFloorArea,-1,-1;\
        uro_BuildingDetailAttribute_buildingRoofEdgeArea "uro_建物利用現況_図形面積" \
        true true false 8 Double 0 0,First,#,{lod1_building_tmp1},\
        uro_BuildingDetailAttribute_buildingRoofEdgeArea,-1,-1;\
        zone_code "zone_code" true true false 255 Text 0 0,First,#,\
        {lod1_building_tmp1},zone_code,0,255;\
        display_high_median "display_high_median" true true false 8 Double 0 0\
        ,First,#,{lod1_building_tmp1},display_high_median,-1,-1;\
        IntegratedAreaID "IntegratedAreaID" true true false 255 Text 0 0,First\
        ,#,{integrated_area},uro_buildingIDAttribute_buildingID,0,255',
        match_option="HAVE_THEIR_CENTER_IN",
        search_radius=None,
        distance_field_name="",
    )
    arcpy.management.JoinField(
        in_data=lod1_building,
        in_field="uro_buildingIDAttribute_buildingID",
        join_table=lod1_building_tmp2,
        join_field="uro_buildingIDAttribute_buildingID",
        fields="IntegratedAreaID"
    )
    arcpy.management.Delete([lod1_building_tmp1, lod1_building_tmp2])


# 将来建築物FootPrint(FootPrint)にフィールド（IntegratedAreaID）を追加
def add_integrated_area_id_foot_print(foot_print, integrated_area):
    bld_foot_print_tmp = os.path.join(intermediate_fgdb, "FootPrint_tmp")
    arcpy.analysis.SpatialJoin(
        target_features=foot_print,
        join_features=integrated_area,
        out_feature_class=bld_foot_print_tmp,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        # 統合エリアデータ（IntegratedArea）のuro_建築物識別情報_建物ID(uro_buildingIDAttribute_buildingID）の値を付与する。
        field_mapping=f'Shape_Length "Shape_Length" false true true 8 Double \
            0 0,First,#,{foot_print},Shape_Length,-1,-1;Shape_Area \
            "Shape_Area" false true true 8 Double 0 0,First,#,\
            {foot_print},Shape_Area,-1,-1;\
            uro_buildingIDAttribute_buildingID \
            "uro_buildingIDAttribute_buildingID" true true false 255 Text 0 0,\
            First,#,{foot_print},uro_buildingIDAttribute_buildingID,0,\
            255;IntegratedAreaID "IntegratedAreaID" true true false 255 Text \
            0 0,First,#,{integrated_area},\
            uro_buildingIDAttribute_buildingID,0,255',
        match_option="HAVE_THEIR_CENTER_IN",
        search_radius=None,
        distance_field_name="",
    )
    arcpy.management.JoinField(
        in_data=foot_print,
        in_field="uro_buildingIDAttribute_buildingID",
        join_table=bld_foot_print_tmp,
        join_field="uro_buildingIDAttribute_buildingID",
        fields="IntegratedAreaID"
    )
    arcpy.management.Delete(bld_foot_print_tmp)


# 「前面道路幅員」(dorowidth)の付与
def set_dorowidth(lod1_building, road_nw_out):
    # 道路NW_一時
    road_nw_tmp = os.path.join(intermediate_fgdb, "road_nw_tmp")
    # フィールド追加用
    lod1_building_join = os.path.join(intermediate_fgdb, "lod1_Building_join")
    output_tmp = os.path.join(intermediate_fgdb, "lod1_Building_tmp")
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=lod1_building,
        out_path=os.path.dirname(lod1_building_join),
        out_name=os.path.basename(lod1_building_join),
    )
    # -1mずつバッファしてwidthを建築物データに設定する
    # 建築物データ（lod1_Building）に、フィールド「前面道路幅員」(dorowidth)を追加する。
    arcpy.management.AddField(
        in_table=lod1_building_join,
        field_name="dorowidth",
        field_type="DOUBLE",
        field_alias="前面道路幅員"
    )
    input = lod1_building_join
    for counter in range(30):
        output = output_tmp + str(counter)
        road_nw_target = road_nw_out
        if counter > 0:
            meters = f"-{str(counter)} Meters"
            arcpy.analysis.Buffer(
                in_features=road_nw_out,
                out_feature_class=road_nw_tmp,
                buffer_distance_or_field=meters,
            )
            road_nw_target = road_nw_tmp
        # 道路と接する建物に対して、widthを設定
        arcpy.analysis.SpatialJoin(
            target_features=input,
            join_features=road_nw_target,
            out_feature_class=output,
            join_operation="JOIN_ONE_TO_ONE",
            join_type="KEEP_ALL",
            # road_nw_tmpのWidth_tmpの値をlod1_Buildingのdorowidthに付与する。
            field_mapping=f'uro_buildingIDAttribute_buildingID \
                "uro_建築物識別情報_建物ID" true true false 50 Text 0 0,\
                First,#,{input},uro_buildingIDAttribute_buildingID,0,50;\
                dorowidth "前面道路幅員" true true false 8 Double 0 0,\
                First,#,{road_nw_target},Width_tmp,-1,-1,\
                {output},dorowidth,-1,-1',
            match_option="INTERSECT",
            search_radius=None,
            distance_field_name="",
        )
        arcpy.management.Delete(input, road_nw_tmp)
        input = output
    # 選択したものを結合
    arcpy.management.JoinField(
        in_data=lod1_building,
        in_field="uro_buildingIDAttribute_buildingID",
        join_table=input,
        join_field="uro_buildingIDAttribute_buildingID",
        fields="dorowidth"
    )
    arcpy.management.Delete(input, road_nw_out)


# ゾーンコードの付与のし直し
def set_zone_code_r(zone_polygon, lod1_building):
    # ここで作成したCursorが別のカーソルにぶつかってしまうので、zone_codeのlistのみ取得
    zone_code_list = []
    with arcpy.da.SearchCursor(zone_polygon, ["zone_code"]) as cur:
        for row in cur:
            zone_code_list.append(row[0])
    # zone_code分繰り返し
    for zone_code in zone_code_list:
        zone_code_str = f"'{zone_code}'"

        zone_polygon_select = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=zone_polygon,
            where_clause=f"zone_code = {zone_code_str}",
        )

        lod1_building_select = arcpy.management.SelectLayerByLocation(
            in_layer=lod1_building,
            overlap_type="HAVE_THEIR_CENTER_IN",
            select_features=zone_polygon_select,
        )
        # ゾーンコードを付与
        arcpy.management.CalculateField(
            in_table=lod1_building_select,
            field="zone_code",
            expression=zone_code_str
        )
        arcpy.management.Delete(zone_polygon_select, lod1_building_select)
    # フィールド追加
    arcpy.management.AddFields(
        in_table=lod1_building,
        field_description=[
            ["BuildingAge", "LONG"],
            ["Integrated_buildingID", "TEXT"],
            ["SimTargetFlag", "LONG"],
        ],
    )


# フィールドの操作
def operate_field():
    # FootprintAreaの値の更新
    arcpy.management.CalculateGeometryAttributes(
        in_features=building,
        geometry_property="FootprintArea AREA",
        area_unit="SQUARE_METERS")

    # 統合建物ID付与
    integrated_building_id_list = []
    with arcpy.da.SearchCursor(integrated_foot_print,
                               ["uro_buildingIDAttribute_buildingID"]) as cur:
        for row in cur:
            integrated_building_id_list.append(row[0])
    # 統合建物ID分繰り返し
    for integrated_building_id in integrated_building_id_list:
        integrated_building_id_str = f"'{integrated_building_id}'"

        integrated_foot_print_select = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=integrated_foot_print,
            where_clause=f"uro_buildingIDAttribute_buildingID = \
            {integrated_building_id_str}",
        )

        building_select = arcpy.management.SelectLayerByLocation(
            in_layer=building,
            overlap_type="INTERSECT",
            select_features=integrated_foot_print_select,
        )
        # 統合建物ID付与
        arcpy.management.CalculateField(
            in_table=building_select,
            field="Integrated_buildingID",
            expression=integrated_building_id_str
        )
        arcpy.management.Delete(
            integrated_foot_print_select, building_select)

    # シミュレーション対象フラグ付与
    code_block = """def judgeSimulationTrflg(Usage, BuildingID):
    if Usage in ["402", "404", "411", "412", "413", "414"]:
        return 1
    elif BuildingID.startswith('FP'):
        return 1
    else:
        return 0"""
    arcpy.management.CalculateField(
        in_table=building,
        field="SimTargetFlag",
        expression="judgeSimulationTrflg(!Usage!, !buildingID!)",
        code_block=code_block,
    )


# "建築物_現況"作成
def create_building(lod1_building):
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=lod1_building,
        out_path=os.path.dirname(building),
        out_name=os.path.basename(building),
        field_mapping=f'buildingID "buildingID" true true false 255 Text 0 \
            0,First,#,{lod1_building},uro_buildingIDAttribute_buildingID,0,\
            50;Usage "Usage" true true false 255 Text 0 0,First,#,\
            {lod1_building},bldg_usage1,0,10;YearOfConstruction \
            "YearOfConstruction" true true false 255 Long 0 0,First,#,\
            {lod1_building},bldg_yearOfConstruction,0,10;Height "Height" \
            true true false 255 Double 0 0,First,#,{lod1_building},\
            display_high_median,0,512;storeysAboveGround "storeysAboveGround" \
            true true false 255 Long 0 0,First,#,{lod1_building},\
            bldg_storeysAboveGround,-1,-1;totalFloorArea "totalFloorArea" \
            true true false 255 Double 0 0,First,#,{lod1_building},\
            uro_BuildingDetailAttribute_totalFloorArea,-1,-1;\
            FootprintArea "FootprintArea" true true false 255 Double 0 0,First,\
            #,{lod1_building},\
            uro_BuildingDetailAttribute_buildingRoofEdgeArea,-1,-1;Existing \
            "Existing" true true false 255 Long 0 0,First,#,{lod1_building},\
            Existing,-1,-1;RoadWidth "RoadWidth" true true false 255 Double 0 \
            0,First,#,{lod1_building},dorowidth,-1,-1;zone_code "zone_code" \
            true true false 255 Text 0 0,First,#,\
            {lod1_building},zone_code,0,255;BuildingAge "BuildingAge" \
            true true false 255 Long 0 0,First,#,{lod1_building},BuildingAge,\
            -1,-1;Integrated_buildingID "Integrated_buildingID" \
            true true false 255 Text 0 0,First,#,{lod1_building},\
            Integrated_buildingID,0,255;SimTargetFlag "SimTargetFlag" \
            true true false 255 Long 0 0,First,#,{lod1_building},SimTargetFlag,\
            -1,-1;Lat "Lat" true true false 255 Double 0 0,First,#,{lod1_building},\
            Lat,-1,-1;Lon "Lon" true true false 255 Double 0 0,First,#,\
            {lod1_building},Lon,-1,-1;ConpletionFlag_Usage \
            "ConpletionFlag_Usage" true true false 255 Long 0 0,First,#,\
            {lod1_building},ConpletionFlag_Usage,-1,-1;ConpletionFlag_Storeys \
            "ConpletionFlag_Storeys" true true false 255 Long 0 0,First,#,\
            {lod1_building},ConpletionFlag_Storeys,-1,-1;ConpletionFlag_FloorArea \
            "ConpletionFlag_FloorArea" true true false 255 Long 0 0,First,#,\
            {lod1_building},ConpletionFlag_FloorArea,-1,-1;ConpletionFlag_Age \
            "ConpletionFlag_Age" true true false 255 Long 0 0,First,#,\
            {lod1_building},ConpletionFlag_Age,-1,-1',
    )


# 建築物別最寄り駅距離データ作成
def create_dist_building_station(station_tmp, station_location, building_now,
      dist_building_station_tmp, dist_building_station):
    # 鉄道駅位置データ.csvを読み込み、ポイントを発生させ、鉄道駅データ（Station）を作成する。また、すべて属性値を付与する。
    out_sr = arcpy.SpatialReference()
    out_sr.loadFromString(out_coordinate_system)
    arcpy.management.XYTableToPoint(
        in_table=station_location,
        out_feature_class=station_tmp,
        x_field="Lon",
        y_field="Lat",
        coordinate_system=6668   # 地理座標系（JGD2011）で固定
    )
    in_coor_system_sta = arcpy.Describe(station_tmp).spatialReference
    arcpy.management.Project(
        in_dataset=station_tmp,
        out_dataset=station,
        in_coor_system=in_coor_system_sta,
        out_coor_system=out_coordinate_system
    )
    arcpy.management.Delete(station_tmp)
    # 建築物_現況をコピーし、建築物別最寄り駅距離データ（lod1_Building_station）を作成する。
    dist_building_station = os.path.join(output_fgdb, "Dist_Building_Station")
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=building_now,
        out_path=os.path.dirname(dist_building_station),
        out_name=os.path.basename(dist_building_station),
        # uro_建築物識別情報_建物ID（uro_buildingIDAttribute_buildingID）を除き、属性項目を削除する。
        field_mapping=f'buildingID "buildingID" \
            true true false 50 Text 0 0,First,#,{building_now},\
            buildingID,0,50',
    )
    # 建物の重心ポイントレイヤー作成
    arcpy.management.CalculateGeometryAttributes(
        in_features=dist_building_station,
        geometry_property="CENTROID_X CENTROID_X;CENTROID_Y CENTROID_Y",
    )
    # 投影法変換要パラメータ
    out_sr = arcpy.SpatialReference()
    out_sr.loadFromString(out_coordinate_system)
    arcpy.management.XYTableToPoint(
        in_table=dist_building_station,
        out_feature_class=dist_building_station_tmp,
        x_field="CENTROID_X",
        y_field="CENTROID_Y",
        coordinate_system=out_sr.factoryCode
    )


# Dist_Building_StationのCSV出力
def output_dist_building_station(dist_building_station, dist_building_station_tmp):
    # Dist_Building_StationのCSV出力
    dist_building_station_csv_tmp = os.path.join(
        output_dir_path, "Dist_Building_Station_tmp.csv")
    arcpy.conversion.ExportTable(
        in_table=dist_building_station,
        out_table=dist_building_station_csv_tmp,
        use_field_alias_as_name="NOT_USE_ALIAS",
        field_mapping=f'buildingID "buildingID" true true false 50 Text 0 0,\
            First,#,{dist_building_station},buildingID,0,50;Dist_sta_centre \
            "Dist_sta_centre" true true false 4 Float 0 0,First,#,\
            {dist_building_station},Dist_sta_centre,-1,-1;Dist_sta_main \
            "Dist_sta_main" true true false 4 Float 0 0,First,#,\
            {dist_building_station},Dist_sta_main,-1,-1;Dist_sta_other \
            "Dist_sta_other" true true false 4 Float 0 0,First,#,\
            {dist_building_station},Dist_sta_other,-1,-1',
        sort_field=None
    )
    dbs_df = pd.read_csv(dist_building_station_csv_tmp)
    dbs_df.drop(dbs_df.columns[0], axis=1).to_csv(
        os.path.join(output_dir_path, "Dist_Building_Station.csv"),
        index=False)
    arcpy.management.Delete(
        [dist_building_station_tmp, dist_building_station_csv_tmp])


# Building.csvの出力
def output_building_csv(building_now):
        # BuildingのCSV出力
    building_csv_tmp = os.path.join(output_dir_path, "Building_tmp.csv")
    arcpy.conversion.ExportTable(
        in_table=building_now,
        out_table=building_csv_tmp,
        use_field_alias_as_name="NOT_USE_ALIAS",
        field_mapping=f'buildingID "buildingID" true true false 255 Text 0 0,\
            First,#,{building_now},buildingID,0,255;Usage "Usage" true true \
            false 255 Text 0 0,First,#,{building_now},Usage,0,255;\
            YearOfConstruction "YearOfConstruction" true true false 255 Text \
            0 0,First,#,{building_now},YearOfConstruction,0,255;Height \
            "Height" true true false 255 Text 0 0,First,#,{building_now},\
            Height,0,255;storeysAboveGround "storeysAboveGround" true true \
            false 255 Text 0 0,First,#,{building_now},storeysAboveGround,0,\
            255;totalFloorArea "totalFloorArea" true true false 255 Text 0 0,\
            First,#,{building_now},totalFloorArea,0,255;FootprintArea \
            "FootprintArea" true true false 255 Text 0 0,First,#,\
            {building_now},FootprintArea,0,255;Existing "Existing" true true \
            false 255 Text 0 0,First,#,{building_now},Existing,0,255;\
            RoadWidth "RoadWidth" true true false 255 Text 0 0,First,#,\
            {building_now},RoadWidth,0,255;zone_code "zone_code" true true \
            false 255 Text 0 0,First,#,{building_now},zone_code,0,255;\
            BuildingAge "BuildingAge" true true false 4 Long 0 0,First,#,\
            {building_now},BuildingAge,-1,-1;Integrated_buildingID \
            "Integrated_buildingID" true true false 255 Text 0 0,First,#,\
            {building_now},Integrated_buildingID,0,255;SimTargetFlag \
            "SimTargetFlag" true true false 4 Long 0 0,First,#,{building_now},\
            SimTargetFlag,0,255;Lat "Lat" true true false 255 Text 0 0,First,#,\
            {building_now},Lat,0,255;Lon "Lon" true true false 255 Text 0 0,\
            First,#,{building_now},Lon,0,255;ConpletionFlag_Usage \
            "ConpletionFlag_Usage" true true false 255 Text 0 0,First,#,\
            {building_now},ConpletionFlag_Usage,0,255;ConpletionFlag_Storeys \
            "ConpletionFlag_Storeys" true true false 255 Text 0 0,First,#,\
            {building_now},ConpletionFlag_Storeys,0,255;ConpletionFlag_FloorArea \
            "ConpletionFlag_FloorArea" true true false 255 Text 0 0,First,#,\
            {building_now},ConpletionFlag_FloorArea,0,255;ConpletionFlag_Age \
            "ConpletionFlag_Age" true true false 255 Text 0 0,First,#,\
            {building_now},ConpletionFlag_Age,0,255',
    )
    # 不要なフィールド削除
    b_df = pd.read_csv(building_csv_tmp)
    b_df.drop(b_df.columns[0], axis=1).to_csv(
        os.path.join(output_dir_path, "Building.csv"), index=False)
    arcpy.management.Delete(building_csv_tmp)


# 建築物別最寄り駅距離データ（Dist_Building_Station）にフィールド追加
def add_field_dist_building_station(dist_building_station_tmp, dist_building_station):
    arcpy.management.AddFields(
        in_table=dist_building_station_tmp,
        field_description=[
            ["Dist_sta_centre", "FLOAT"],
            ["Dist_sta_main", "FLOAT"],
            ["Dist_sta_other", "FLOAT"],
        ],
    )

    for count in range(1, 4):
        field = ""
        if count == 1:
            field = "Dist_sta_centre"
        elif count == 2:
            field = "Dist_sta_main"
        elif count == 3:
            field = "Dist_sta_other"
        sql = f"Station_Flag = {str(count)}"
        targets = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=station,
            selection_type="NEW_SELECTION",
            where_clause=sql,
        )
        arcpy.analysis.Near(
            in_features=dist_building_station_tmp,
            near_features=targets,
            field_names=f"NEAR_DIST {field}",
        )
        arcpy.management.Delete(targets)

    # 一時テーブルから移動
    arcpy.management.JoinField(
        in_data=dist_building_station,
        in_field="buildingID",
        join_table=dist_building_station_tmp,
        join_field="buildingID",
        fields=["Dist_sta_centre", "Dist_sta_main", "Dist_sta_other"],
    )
    # 不要なフィールド削除
    arcpy.management.DeleteField(
        in_table=dist_building_station, drop_field=["CENTROID_X", "CENTROID_Y"]
    )


# 内側バッファ処理メソッド
def buffer_inside_loop(input, output, layer1, layer2, res_layer):
    # バッファ用出力レイヤー切替フラグ
    switch = True
    # 計算用面積割り出し(ループ前)
    arcpy.management.CalculateGeometryAttributes(
        in_features=input,
        geometry_property="area_calc AREA",
        area_unit="SQUARE_METERS",
    )
    # 比較用建蔽率割り出し(ループ前)
    arcpy.management.AddField(
        in_table=input,
        field_name="urf_buildingCoverageRate_comparison",
        field_type="DOUBLE",
    )
    arcpy.management.CalculateField(
        in_table=input,
        field="urf_buildingCoverageRate_comparison",
        expression="!area_calc! / !area_first!",
    )
    # 格納用レイヤー作成
    arcpy.conversion.ExportFeatures(
        in_features=input,
        out_features=res_layer,
        where_clause="OBJECTID IS NULL"
    )
    # 内側バッファ対象が0になるまで実施
    while True:
        # 内側に1mずつバッファ
        arcpy.analysis.Buffer(
            in_features=input,
            out_feature_class=output,
            buffer_distance_or_field="-1 Meters",
        )
        # 不要なフィールド削除
        arcpy.management.DeleteField(
            in_table=output, drop_field=["BUFF_DIST", "ORIG_FID"]
        )
        # 計算用面積割り出し
        arcpy.management.CalculateGeometryAttributes(
            in_features=output,
            geometry_property="area_calc AREA",
            area_unit="SQUARE_METERS",
        )
        # 比較用建蔽率割り出し
        arcpy.management.CalculateField(
            in_table=output,
            field="urf_buildingCoverageRate_comparison",
            expression="!area_calc! / !area_first!",
        )
        # 格納対象フィーチャ抽出
        output_select = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=output,
            selection_type="NEW_SELECTION",
            where_clause="urf_buildingCoverageRate >= \
                urf_buildingCoverageRate_comparison",
        )
        # 計算した建蔽率がutf_建蔽率より小さいフィーチャを格納用レイヤーに格納
        arcpy.management.Append(inputs=output_select, target=res_layer)
        # 格納したレイヤーは対象外にする
        arcpy.management.DeleteRows(output_select)
        # 次の処理対象が存在するか確認
        layer, count = arcpy.management.SelectLayerByAttribute(
            in_layer_or_view=output,
            selection_type="NEW_SELECTION",
            where_clause="urf_buildingCoverageRate < \
                urf_buildingCoverageRate_comparison",
        )

        # 次の処理対象が存在しない場合、ループを抜ける
        if int(count) <= 0:
            break

        if switch:
            input = layer1
            output = layer2
            switch = False
        else:
            input = layer2
            output = layer1
            switch = True

    arcpy.management.Delete([layer1, layer2])


# 建築物の面積2500㎡以上を対象の用途に「999」を付与する。
def set_usage_999(lod1_building):
    # 面積フィールドの追加
    arcpy.management.CalculateGeometryAttributes(
        in_features=lod1_building,
        geometry_property="area_tmp AREA",
        area_unit="SQUARE_METERS")
    # 属性検索で面積が2500㎡以上かつ、用途が空欄のものを抽出
    lod1_building_select = arcpy.management.SelectLayerByAttribute(
        lod1_building,
        "NEW_SELECTION",
        "area_tmp >= 2500 and (bldg_usage1 = '' or bldg_usage1 IS NULL)"
    )
    # 抽出したレコードに対してフィールド演算で用途に「999」を設定する
    arcpy.management.CalculateField(
            in_table=lod1_building_select,
            field="bldg_usage1",
            expression='"999"',
    )
    # 補間フラグも立てる
    arcpy.management.CalculateField(
            in_table=lod1_building_select,
            field="ConpletionFlag_Usage",
            expression='1',
    )
    # 面積フィールドを削除
    arcpy.management.DeleteField(
        in_table=lod1_building,
        drop_field="area_tmp"
    )


# ログの設定
def set_log_format(name, log_file_path=log_file_path):
    logger = logging.getLogger(name)
    logger.disabled = False
    logger.setLevel(logging.INFO)
    if len(logger.handlers) == 0:
        handler = logging.FileHandler(log_file_path)
        handler.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s [%(name)s] - %(levelname)s - %(message)s"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


# 異常ログ出力メソッド
def logging_error(message, exception, log):

    log.error(message)
    log.exception("%s", exception)


# This is used to execute code if the file was run but not imported
if __name__ == "__main__":
    # Tool parameter accessed with GetParameter or GetParameterAsText
    lod1_building = arcpy.GetParameterAsText(0)
    lod1_use_district = arcpy.GetParameterAsText(1)
    lod1_land_use = arcpy.GetParameterAsText(2)
    zone_polygon = arcpy.GetParameterAsText(3)
    road_nw = arcpy.GetParameterAsText(4)
    station_location = arcpy.GetParameterAsText(5)
    out_coordinate_system = arcpy.GetParameterAsText(6)

    script_tool(
        arcpy.GetParameterAsText(0),
        arcpy.GetParameterAsText(1),
        arcpy.GetParameterAsText(2),
        arcpy.GetParameterAsText(3),
        arcpy.GetParameterAsText(4),
        arcpy.GetParameterAsText(5),
        arcpy.GetParameterAsText(6),
    )
