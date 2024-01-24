"""
シナリオ設定UI機能
"""

import csv
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Union

import arcpy  # type: ignore
import numpy as np
import pandas as pd

# ゾーンデータの中間ファイル出力パス
ZONE_DATA_TMP = r"memory\Zone_tmp"
# ログ出力先パス
ROOT_DIR_PATH = Path(__file__).parents[2]
PROJECT_ROOT_PATH = os.path.abspath(ROOT_DIR_PATH)

# 用途地域のコードの設定
USAGE_CODES = {
    "第一種低層住居専用地域": "1",
    "第二種低層住居専用地域": "2",
    "第一種中高層住居専用地域": "3",
    "第二種中高層住居専用地域": "4",
    "第一種住居地域": "5",
    "第二種住居地域": "6",
    "準住居地域": "7",
    "近隣商業地域": "8",
    "商業地域": "9",
    "準工業地域": "10",
    "工業地域": "11",
    "工業専用地域": "12",
    "田園住居地域": "21",
    "市街化区域外": "99",
}


class SenarioSettingException(Exception):
    pass


def create_user_input_data(
    data: Optional[list[list[Union[int, str, None]]]] = None
):
    return pd.DataFrame(
        data,
        index=["user_data"],
        columns=[
            "scenario_name",
            "zone_code",
            "scenario_start_year",
            "scenario_end_year",
            "fnum_Library",
            "fnum_Hospital",
            "fnum_ElementarySchool",
            "fnum_MiddleSchool",
            "fnum_PreSchool",
            "facility_start_year",
            "facility_end_year",
            "usage",
            "floorAreaRate",
            "city_start_year",
            "city_end_year",
            "ChangeRateCommercial",
            "ChangeRateResidence",
            "land_start_year",
            "land_end_year",
            "Migration_Rate_In",
            "Migration_Rate_Out",
            "migration_start_year",
            "migration_end_year",
            "Travel_Time_Rail",
            "Waiting_Time_Rail",
            "Access_Time_Rail",
            "Egress_Time_Rail",
            "Fare_Rail",
            "Waiting_Time_Bus",
            "Fare_Bus",
            "traffic_start_year",
            "traffic_end_year",
        ],
    )


def get_user_parameter() -> pd.DataFrame:
    """
    ユーザ入力パラメータの読込とバリデーションチェックを行う。
    ジオプロセシングツールのパラメータではStringを設定することパラメータの順番は
    「user_input_data_type」と一致させること
    引数：

    返値：
        user_input_data[Series型]:ユーザ入力を格納したデータフレーム

    入力:
        ジオプロセシングツールのUIで入力された値

    """
    # [入力パラメータの取得]
    # ユーザ入力直接の文字列を直接に確認する一次変数をusr_str_*と名前付ける
    usr_str_scenario_name: str = arcpy.GetParameterAsText(0)  # シナリオ名
    usr_str_zone_polygon_path: str = arcpy.GetParameterAsText(1)  # ゾーンポリゴンのパス
    usr_str_scenario_start_year: str = arcpy.GetParameterAsText(2)  # シナリオ開始年次
    usr_str_scenario_end_year: str = arcpy.GetParameterAsText(3)  # シナリオ終了年次
    usr_str_fnum_library: str = arcpy.GetParameterAsText(4)  # 図書館の数
    usr_str_fnum_hospital: str = arcpy.GetParameterAsText(5)  # 病院の数
    usr_str_fnum_elementary_school: str = arcpy.GetParameterAsText(6)  # 小学校の数
    usr_str_fnum_junior_high_school: str = arcpy.GetParameterAsText(7)  # 中学校の数
    usr_str_fnum_kindergarten: str = arcpy.GetParameterAsText(8)  # 幼稚園および子供園の数
    usr_str_facility_start_year: str = arcpy.GetParameterAsText(9)  # 施設数の開始年次
    usr_str_facility_end_year: str = arcpy.GetParameterAsText(10)  # 施設数の終了年次
    usr_str_usage: str = arcpy.GetParameterAsText(11)  # 用途地域
    usr_str_floor_area_rate: str = arcpy.GetParameterAsText(12)  # 容積率
    usr_str_city_start_year: str = arcpy.GetParameterAsText(13)  # 都市情報の開始年次
    usr_str_city_end_year: str = arcpy.GetParameterAsText(14)  # 都市情報の終了年次
    usr_str_change_rate_commercial: str = arcpy.GetParameterAsText(
        15
    )  # 商業地価変更割合
    usr_str_change_rate_residence: str = arcpy.GetParameterAsText(
        16
    )  # 住宅地価変更割合
    usr_str_land_start_year: str = arcpy.GetParameterAsText(17)  # 地価変更割合の開始年次
    usr_str_land_end_year: str = arcpy.GetParameterAsText(18)  # 地価変更割合の終了年次
    usr_str_migration_rate_in: str = arcpy.GetParameterAsText(19)  # 転入率
    usr_str_migration_rate_out: str = arcpy.GetParameterAsText(20)  # 転出率
    usr_str_migration_start_year: str = arcpy.GetParameterAsText(
        21
    )  # 転入転出割合の開始年次
    usr_str_migration_end_year: str = arcpy.GetParameterAsText(
        22
    )  # 転入転出割合の終了年次
    usr_str_travel_time_rail: str = arcpy.GetParameterAsText(23)  # 鉄道乗車時間
    usr_str_waiting_time_rail: str = arcpy.GetParameterAsText(24)  # 鉄道待ち時間
    usr_str_access_time_rail: str = arcpy.GetParameterAsText(25)  # 鉄道アクセス時間
    usr_str_egress_time_rail: str = arcpy.GetParameterAsText(26)  # 鉄道イグレス時間
    usr_str_fare_rail: str = arcpy.GetParameterAsText(27)  # 鉄道運賃
    usr_str_waiting_time_bus: str = arcpy.GetParameterAsText(28)  # バス待ち時間
    usr_str_fare_bus: str = arcpy.GetParameterAsText(29)  # バス運賃
    usr_str_traffic_start_year: str = arcpy.GetParameterAsText(
        30
    )  # 公共交通情報の開始年次
    usr_str_traffic_end_year: str = arcpy.GetParameterAsText(31)  # 公共交通情報の終了年次

    # ユーザ入力データを格納するデータフレーム定義する
    user_input_data = create_user_input_data()

    # [入力パラメータのバリデーションチェック]
    # 単なる文字列はそのまま明示的にコピーする
    # Text(0) 必須入力 入力がない場合はジオプロセシングツールでチェックを行う
    user_input_data.at["user_data", "scenario_name"] = usr_str_scenario_name

    # Text(1) 必須入力 入力がない場合はジオプロセシングツールでチェックを行う
    user_input_data.at["user_data", "zone_code"] = get_zone_codes(
        usr_str_zone_polygon_path
    )

    # Text(2)
    # シナリオの開始年次 必須入力 入力がない場合はジオプロセシングツールでチェックを行う
    # int型にキャストしてバリデーションチェックを行う
    try:
        user_input_data.at["user_data", "scenario_start_year"] = int(
            usr_str_scenario_start_year
        )
        if (
            user_input_data.at["user_data", "scenario_start_year"] < 2015
            or 2040 < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: シナリオの開始年次が2015以上2040以下の整数ではありません："
                + usr_str_scenario_start_year
            )
    except ValueError:
        raise ValueError(
            "Error: シナリオの開始年次が2015以上2040以下の整数ではありません："
            + usr_str_scenario_start_year
        )

    # Text(3)
    # シナリオの終了年次 必須入力 入力がない場合はジオプロセシングツールでチェックを行う
    # int型にキャストしてバリデーションチェックを行う
    try:
        user_input_data.at["user_data", "scenario_end_year"] = int(
            usr_str_scenario_end_year
        )
        if (
            user_input_data.at["user_data", "scenario_end_year"] < 2015
            or 2040 < user_input_data.at["user_data", "scenario_end_year"]
        ):
            raise SenarioSettingException(
                "Error: シナリオの終了年次が2015以上2040以下の整数ではありません："
                + usr_str_scenario_end_year
            )
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: シナリオの終了年次が開始年次以上の整数ではありません："
                + usr_str_scenario_end_year
            )
    except ValueError:
        raise ValueError(
            "Error: シナリオの終了年次が2015以上2040以下の整数ではありません："
            + usr_str_scenario_end_year
        )

    # Text(4)
    # 図書館の数 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_fnum_library == "":
        user_input_data.at["user_data", "fnum_Library"] = -1
    else:
        try:
            user_input_data.at["user_data", "fnum_Library"] = int(
                usr_str_fnum_library
            )
            if (
                user_input_data.at["user_data", "fnum_Library"] < 0
                or 9 < user_input_data.at["user_data", "fnum_Library"]
            ):
                raise SenarioSettingException(
                    "Error: 図書館の数が0以上9以下の整数ではありません"
                    + "："
                    + usr_str_fnum_library
                )
        except ValueError:
            raise ValueError(
                "Error: 図書館の数が0以上9以下の整数ではありません" + "：" + usr_str_fnum_library
            )

    # Text(5)
    # 病院の数 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_fnum_hospital == "":
        user_input_data.at["user_data", "fnum_Hospital"] = -1
    else:
        try:
            user_input_data.at["user_data", "fnum_Hospital"] = int(
                usr_str_fnum_hospital
            )
            if (
                user_input_data.at["user_data", "fnum_Hospital"] < 0
                or 9 < user_input_data.at["user_data", "fnum_Hospital"]
            ):
                raise SenarioSettingException(
                    "Error: 病院の数が0以上9以下の整数ではありません" + "：" + usr_str_fnum_library
                )
        except ValueError:
            raise ValueError(
                "Error: 病院の数が0以上9以下の整数ではありません" + "：" + usr_str_fnum_library
            )

    # Text(6)
    # 小学校の数 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_fnum_elementary_school == "":
        user_input_data.at["user_data", "fnum_ElementarySchool"] = -1
    else:
        try:
            user_input_data.at["user_data", "fnum_ElementarySchool"] = int(
                usr_str_fnum_elementary_school
            )
            if (
                user_input_data.at["user_data", "fnum_ElementarySchool"] < 0
                or 9 < user_input_data.at["user_data", "fnum_ElementarySchool"]
            ):
                raise SenarioSettingException(
                    "Error: 小学校の数が0以上9以下の整数ではありません"
                    + "："
                    + usr_str_fnum_elementary_school
                )
        except ValueError:
            raise ValueError(
                "Error: 小学校の数が0以上9以下の整数ではありません"
                + "："
                + usr_str_fnum_elementary_school
            )

    # Text(7)
    # 中学校の数 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_fnum_junior_high_school == "":
        user_input_data.at["user_data", "fnum_MiddleSchool"] = -1
    else:
        try:
            user_input_data.at["user_data", "fnum_MiddleSchool"] = int(
                usr_str_fnum_junior_high_school
            )
            if (
                user_input_data.at["user_data", "fnum_MiddleSchool"] < 0
                or 9 < user_input_data.at["user_data", "fnum_MiddleSchool"]
            ):
                raise SenarioSettingException(
                    "Error: 中学校の数が0以上9以下の整数ではありません"
                    + "："
                    + usr_str_fnum_junior_high_school
                )
        except ValueError:
            raise ValueError(
                "Error: 中学校の数が0以上9以下の整数ではありません"
                + "："
                + usr_str_fnum_junior_high_school
            )

    # Text(8)
    # 幼稚園及びこども園 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_fnum_kindergarten == "":
        user_input_data.at["user_data", "fnum_PreSchool"] = -1
    else:
        try:
            user_input_data.at["user_data", "fnum_PreSchool"] = int(
                usr_str_fnum_kindergarten
            )
            if (
                user_input_data.at["user_data", "fnum_PreSchool"] < 0
                or 9 < user_input_data.at["user_data", "fnum_PreSchool"]
            ):
                raise SenarioSettingException(
                    "Error: 幼稚園及びこども園の数が0以上9以下の整数ではありません"
                    + "："
                    + usr_str_fnum_kindergarten
                )
        except ValueError:
            raise ValueError(
                "Error: 幼稚園及びこども園の数が0以上9以下の整数ではありません"
                + "："
                + usr_str_fnum_kindergarten
            )

    # Text(9)
    # 施設数の開始年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_facility_start_year == "":
        user_input_data.at["user_data", "facility_start_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "facility_start_year"] = int(
                usr_str_facility_start_year
            )
            if (
                user_input_data.at["user_data", "facility_start_year"] < 2015
                or 2040
                < user_input_data.at["user_data", "facility_start_year"]
            ):
                raise SenarioSettingException(
                    "Error: 施設数の開始年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_facility_start_year
                )
        except ValueError:
            raise ValueError(
                "Error: 施設数の開始年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_facility_start_year
            )

    # Text(10)
    # 施設数の終了年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_facility_end_year == "":
        user_input_data.at["user_data", "facility_end_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "facility_end_year"] = int(
                usr_str_facility_end_year
            )
            if (
                user_input_data.at["user_data", "facility_end_year"] < 2015
                or 2040 < user_input_data.at["user_data", "facility_end_year"]
            ):
                raise SenarioSettingException(
                    "Error: 施設数の終了年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_facility_end_year
                )
        except ValueError:
            raise ValueError(
                "Error: 施設数の終了年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_facility_end_year
            )

    # Text(11)
    # 用途地域 オプション入力 入力がなかった場合空文字が入力される、
    # 空文字以外の場合バリデーションチェックを行う
    if usr_str_usage != "":
        if usr_str_usage in USAGE_CODES:
            user_input_data.at["user_data", "UseDistrict"] = USAGE_CODES.get(
                usr_str_usage
            )
        else:
            raise SenarioSettingException(
                (
                    f"Error: 用途地域は{USAGE_CODES.values()}の値を入力してください"
                    f"．入力されたコードは： {usr_str_usage} です"
                )
            )
    else:
        user_input_data.at["user_data", "UseDistrict"] = ""

    # Text(12)
    # 容積率 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_floor_area_rate == "":
        user_input_data.at["user_data", "floorAreaRate"] = -1
    else:
        try:
            user_input_data.at["user_data", "floorAreaRate"] = int(
                usr_str_floor_area_rate
            )
            if (
                user_input_data.at["user_data", "floorAreaRate"] < 0
                or 9999 < user_input_data.at["user_data", "floorAreaRate"]
            ):
                raise SenarioSettingException(
                    "Error: 容積率の数が0以上9999以下の整数ではありません"
                    + "："
                    + usr_str_floor_area_rate
                )
        except ValueError:
            raise ValueError(
                "Error: 容積率の数が0以上9999以下の整数ではありません"
                + "："
                + usr_str_floor_area_rate
            )

    # Text(13)
    # 都市計画情報の開始年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_city_start_year == "":
        user_input_data.at["user_data", "city_start_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "city_start_year"] = int(
                usr_str_city_start_year
            )
            if (
                user_input_data.at["user_data", "city_start_year"] < 2015
                or 2040 < user_input_data.at["user_data", "city_start_year"]
            ):
                raise SenarioSettingException(
                    "Error: 都市計画情報の開始年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_city_start_year
                )
        except ValueError:
            raise ValueError(
                "Error: 都市計画情報の開始年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_city_start_year
            )

    # Text(14)
    # 都市計画情報の終了年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_city_end_year == "":
        user_input_data.at["user_data", "city_end_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "city_end_year"] = int(
                usr_str_city_end_year
            )
            if (
                user_input_data.at["user_data", "city_end_year"] < 2015
                or 2040 < user_input_data.at["user_data", "city_end_year"]
            ):
                raise SenarioSettingException(
                    "Error: 都市計画情報の終了年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_city_end_year
                )
        except ValueError:
            raise ValueError(
                "Error: 都市計画情報の終了年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_city_end_year
            )

    # Text(15)
    # 商業地価変更割合 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_change_rate_commercial == "":
        user_input_data.at["user_data", "ChangeRateCommercial"] = -1
    else:
        try:
            user_input_data.at["user_data", "ChangeRateCommercial"] = int(
                usr_str_change_rate_commercial
            )
            if (
                user_input_data.at["user_data", "ChangeRateCommercial"] < 0
                or 100
                < user_input_data.at["user_data", "ChangeRateCommercial"]
            ):
                raise SenarioSettingException(
                    "Error: 商業地価変更割合の数が0以上100以下の整数ではありません"
                    + "："
                    + usr_str_change_rate_commercial
                )
        except ValueError:
            raise ValueError(
                "Error: 商業地価変更割合の数が0以上100以下の整数ではありません"
                + "："
                + usr_str_change_rate_commercial
            )

    # Text(16)
    # 住宅地価変更割合 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_change_rate_residence == "":
        user_input_data.at["user_data", "ChangeRateResidence"] = -1
    else:
        try:
            user_input_data.at["user_data", "ChangeRateResidence"] = int(
                usr_str_change_rate_residence
            )
            if (
                user_input_data.at["user_data", "ChangeRateResidence"] < 0
                or 100 < user_input_data.at["user_data", "ChangeRateResidence"]
            ):
                raise SenarioSettingException(
                    "Error: 住宅地価変更割合が0以上100以下の整数ではありません"
                    + "："
                    + usr_str_change_rate_residence
                )
        except ValueError:
            raise ValueError(
                "Error: 住宅地価変更割合が0以上100以下の整数ではありません"
                + "："
                + usr_str_change_rate_residence
            )

    # Text(17)
    # 地価変更割合の開始年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_land_start_year == "":
        user_input_data.at["user_data", "land_start_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "land_start_year"] = int(
                usr_str_land_start_year
            )
            if (
                user_input_data.at["user_data", "land_start_year"] < 2015
                or 2040 < user_input_data.at["user_data", "land_start_year"]
            ):
                raise SenarioSettingException(
                    "Error: 地価変更割合の開始年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_land_start_year
                )
        except ValueError:
            raise ValueError(
                "Error: 地価変更割合の開始年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_land_start_year
            )

    # Text(18)
    #  オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    #  空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_land_end_year == "":
        user_input_data.at["user_data", "land_end_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "land_end_year"] = int(
                usr_str_land_end_year
            )
            if (
                user_input_data.at["user_data", "land_end_year"] < 2015
                or 2040 < user_input_data.at["user_data", "land_end_year"]
            ):
                raise SenarioSettingException(
                    "Error: 地価変更割合の終了年次が2015以上2040以下の整数ではありません"
                    + "："
                    + usr_str_land_end_year
                )
        except ValueError:
            raise ValueError(
                "Error: 地価変更割合の終了年次が2015以上2040以下の整数ではありません"
                + "："
                + usr_str_land_end_year
            )

    # Text(19)
    # 転入率 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_migration_rate_in == "":
        user_input_data.at["user_data", "Migration_Rate_In"] = -1
    else:
        try:
            user_input_data.at["user_data", "Migration_Rate_In"] = int(
                usr_str_migration_rate_in
            )
            if (
                user_input_data.at["user_data", "Migration_Rate_In"] < 0
                or 100 < user_input_data.at["user_data", "Migration_Rate_In"]
            ):
                raise SenarioSettingException(
                    "Error: 転入率が0以上100以下の整数ではありません"
                    + "："
                    + usr_str_migration_rate_in
                )
        except ValueError:
            raise ValueError(
                "Error: 転入率が0以上100以下の整数ではありません"
                + "："
                + usr_str_migration_rate_in
            )

    # Text(20)
    # 転出率 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_migration_rate_out == "":
        user_input_data.at["user_data", "Migration_Rate_Out"] = -1
    else:
        try:
            user_input_data.at["user_data", "Migration_Rate_Out"] = int(
                usr_str_migration_rate_out
            )
            if (
                user_input_data.at["user_data", "Migration_Rate_Out"] < 0
                or 100 < user_input_data.at["user_data", "Migration_Rate_Out"]
            ):
                raise SenarioSettingException(
                    "Error: 転出率が0以上100以下の整数ではありません"
                    + "："
                    + usr_str_migration_rate_out
                )
        except ValueError:
            raise ValueError(
                "Error: 転出率が0以上100以下の整数ではありません"
                + "："
                + usr_str_migration_rate_out
            )

    # Text(21)
    # 転入転出割合の開始年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_migration_start_year == "":
        user_input_data.at["user_data", "migration_start_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "migration_start_year"] = int(
                usr_str_migration_start_year
            )
            if user_input_data.at["user_data", "migration_start_year"] < 0:
                raise SenarioSettingException(
                    "Error: 転入転出割合の開始年次が0以上の整数ではありません"
                    + "："
                    + usr_str_migration_start_year
                )
        except ValueError:
            raise ValueError(
                "Error: 転入転出割合の開始年次が0以上の整数ではありません"
                + "："
                + usr_str_migration_start_year
            )

    # Text(22)
    # 転入転出割合の終了年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_migration_end_year == "":
        user_input_data.at["user_data", "migration_end_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "migration_end_year"] = int(
                usr_str_migration_end_year
            )
            if user_input_data.at["user_data", "migration_end_year"] < 0:
                raise SenarioSettingException(
                    "Error: 転入転出割合の終了年次が0以上の整数ではありません"
                    + "："
                    + usr_str_migration_end_year
                )
        except ValueError:
            raise ValueError(
                "Error: 転入転出割合の終了年次が0以上の整数ではありません"
                + "："
                + usr_str_migration_end_year
            )

    # Text(23)
    # 鉄道乗車時間 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_travel_time_rail == "":
        user_input_data.at["user_data", "Travel_Time_Rail"] = -1
    else:
        try:
            user_input_data.at["user_data", "Travel_Time_Rail"] = float(
                usr_str_travel_time_rail
            )
            if (
                user_input_data.at["user_data", "Travel_Time_Rail"] < 0
                or 100 < user_input_data.at["user_data", "Travel_Time_Rail"]
            ):
                raise SenarioSettingException(
                    "Error: 鉄道乗車時間が0以上100以下の実数ではありません"
                    + "："
                    + usr_str_travel_time_rail
                )
        except ValueError:
            raise ValueError(
                "Error: 鉄道乗車時間が0以上100以下の実数ではありません"
                + "："
                + usr_str_travel_time_rail
            )

    # Text(24)
    # 鉄道待ち時間 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_waiting_time_rail == "":
        user_input_data.at["user_data", "Waiting_Time_Rail"] = -1
    else:
        try:
            user_input_data.at["user_data", "Waiting_Time_Rail"] = float(
                usr_str_waiting_time_rail
            )
            if (
                user_input_data.at["user_data", "Waiting_Time_Rail"] < 0
                or 100 < user_input_data.at["user_data", "Waiting_Time_Rail"]
            ):
                raise SenarioSettingException(
                    "Error: 鉄道待ち時間が0以上100以下の実数ではありません"
                    + "："
                    + usr_str_waiting_time_rail
                )
        except ValueError:
            raise ValueError(
                "Error: 鉄道待ち時間が0以上100以下の実数ではありません"
                + "："
                + usr_str_waiting_time_rail
            )

    # Text(25)
    # 鉄道アクセス時間 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_access_time_rail == "":
        user_input_data.at["user_data", "Access_Time_Rail"] = -1
    else:
        try:
            user_input_data.at["user_data", "Access_Time_Rail"] = float(
                usr_str_access_time_rail
            )
            if (
                user_input_data.at["user_data", "Access_Time_Rail"] < 0
                or 100 < user_input_data.at["user_data", "Access_Time_Rail"]
            ):
                raise SenarioSettingException(
                    "Error: 鉄道アクセス時間が0以上100以下の実数ではありません"
                    + "："
                    + usr_str_access_time_rail
                )
        except ValueError:
            raise ValueError(
                "Error: 鉄道アクセス時間が0以上100以下の実数ではありません"
                + "："
                + usr_str_access_time_rail
            )

    # Text(26)
    # 鉄道イグレス時間 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_egress_time_rail == "":
        user_input_data.at["user_data", "Egress_Time_Rail"] = -1
    else:
        try:
            user_input_data.at["user_data", "Egress_Time_Rail"] = float(
                usr_str_egress_time_rail
            )
            if (
                user_input_data.at["user_data", "Egress_Time_Rail"] < 0
                or 100 < user_input_data.at["user_data", "Egress_Time_Rail"]
            ):
                raise SenarioSettingException(
                    "Error: 鉄道イグレス時間が0以上100以下の実数ではありません"
                    + "："
                    + usr_str_egress_time_rail
                )
        except ValueError:
            raise ValueError(
                "Error: 鉄道イグレス時間が0以上100以下の実数ではありません"
                + "："
                + usr_str_egress_time_rail
            )

    # Text(27)
    # 鉄道運賃 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_fare_rail == "":
        user_input_data.at["user_data", "Fare_Rail"] = -1
    else:
        try:
            user_input_data.at["user_data", "Fare_Rail"] = float(
                usr_str_fare_rail
            )
            if (
                user_input_data.at["user_data", "Fare_Rail"] < 0
                or 100 < user_input_data.at["user_data", "Fare_Rail"]
            ):
                raise SenarioSettingException(
                    "Error: 鉄道運賃が0以上100以下の実数ではありません" + "：" + usr_str_fare_rail
                )
        except ValueError:
            raise ValueError(
                "Error: 鉄道運賃が0以上100以下の実数ではありません" + "：" + usr_str_fare_rail
            )

    # Text(28)
    # バス待ち時間 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_waiting_time_bus == "":
        user_input_data.at["user_data", "Waiting_Time_Bus"] = -1
    else:
        try:
            user_input_data.at["user_data", "Waiting_Time_Bus"] = float(
                usr_str_waiting_time_bus
            )
            if (
                user_input_data.at["user_data", "Waiting_Time_Bus"] < 0
                or 100 < user_input_data.at["user_data", "Waiting_Time_Bus"]
            ):
                raise SenarioSettingException(
                    "Error: バス待ち時間が0以上100以下の実数ではありません"
                    + "："
                    + usr_str_waiting_time_bus
                )
        except ValueError:
            raise ValueError(
                "Error: バス待ち時間が0以上100以下の実数ではありません"
                + "："
                + usr_str_waiting_time_bus
            )

    # Text(29)
    # バス運賃 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合float型にキャストしてバリデーションチェックを行う
    if usr_str_fare_bus == "":
        user_input_data.at["user_data", "Fare_Bus"] = -1
    else:
        try:
            user_input_data.at["user_data", "Fare_Bus"] = float(
                usr_str_fare_bus
            )
            if (
                user_input_data.at["user_data", "Fare_Bus"] < 0
                or 100 < user_input_data.at["user_data", "Fare_Bus"]
            ):
                raise SenarioSettingException(
                    "Error: バス運賃が0以上100以下の実数ではありません" + "：" + usr_str_fare_bus
                )
        except ValueError:
            raise ValueError(
                "Error: バス運賃が0以上100以下の実数ではありません" + "：" + usr_str_fare_bus
            )

    # Text(30)
    # 交通情報の開始年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_traffic_start_year == "":
        user_input_data.at["user_data", "traffic_start_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "traffic_start_year"] = int(
                usr_str_traffic_start_year
            )
            if (
                user_input_data.at["user_data", "traffic_start_year"] < 2015
                or 2040 < user_input_data.at["user_data", "traffic_start_year"]
            ):
                raise SenarioSettingException(
                    "Error: 交通情報の開始年次が2015以上2040以下の整数ではありません："
                    + usr_str_traffic_start_year
                )
        except ValueError:
            raise ValueError(
                "Error: 交通情報の開始年次が2015以上2040以下の整数ではありません："
                + usr_str_traffic_start_year
            )

    # Text(31)
    # 交通情報の終了年次 オプション入力 入力がなかった場合空文字が入力される 空文字の場合識別値として-1を格納し、
    # 空文字以外の場合int型にキャストしてバリデーションチェックを行う
    if usr_str_traffic_end_year == "":
        user_input_data.at["user_data", "traffic_end_year"] = -1
    else:
        try:
            user_input_data.at["user_data", "traffic_end_year"] = int(
                usr_str_traffic_end_year
            )
            if (
                user_input_data.at["user_data", "traffic_end_year"] < 2015
                or 2040 < user_input_data.at["user_data", "traffic_end_year"]
            ):
                raise SenarioSettingException(
                    "Error: 交通情報の終了年次が2015以上2040以下の整数ではありません："
                    + usr_str_traffic_end_year
                )
        except ValueError:
            raise ValueError(
                "Error: 交通情報の終了年次が2015以上2040以下の整数ではありません："
                + usr_str_traffic_end_year
            )

    # [開始年次と終了年次のバリデーションチェック]
    # 施設数の開始年次と終了年次のユーザ入力のバリデーションチェック
    # 施設数にユーザ入力があるか否かを確認する
    if (
        user_input_data.at["user_data", "fnum_Library"] != -1
        or user_input_data.at["user_data", "fnum_Hospital"] != -1
        or user_input_data.at["user_data", "fnum_ElementarySchool"] != -1
        or user_input_data.at["user_data", "fnum_MiddleSchool"] != -1
        or user_input_data.at["user_data", "fnum_PreSchool"] != -1
    ):
        # 施設数にユーザ入力がある場合で施設数の開始年次あるいは終了年次の入力の有無を確認し、ない場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "facility_start_year"] == -1
            or user_input_data.at["user_data", "facility_end_year"] == -1
        ):
            raise SenarioSettingException(
                "Error: 施設数の値を変更する場合開始年次と終了年次を入力してください"
            )
        # 施設数にユーザ入力がある場合で施設数の開始年次がシナリオの開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "facility_start_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 施設数の開始年次はシナリオの開始年次以上の値を入力してください"
            )
        # 施設数にユーザ入力がある場合で施設数の終了年次がシナリオの終了年次より大きい場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "facility_end_year"]
        ):
            raise SenarioSettingException(
                "Error: 施設数の終了年次はシナリオの終了年次以下の値を入力してください"
            )
        # 施設数にユーザ入力がある場合で施設数の終了年次が施設数の開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "facility_end_year"]
            < user_input_data.at["user_data", "facility_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 施設数の終了年次は施設数の開始年次以上の値を入力してください"
            )
    else:
        # 施設数にユーザ入力がない場合で施設数の開始年次あるいは終了年次がある場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "facility_start_year"] != -1
            or user_input_data.at["user_data", "facility_end_year"] != -1
        ):
            raise SenarioSettingException("Error: 施設数の変更する値を入力してください")

    # 都市計画情報の開始年次と終了年次のユーザ入力のバリデーションチェック
    # 都市計画情報にユーザ入力があるか否かを確認する
    if (
        user_input_data.at["user_data", "UseDistrict"] != ""
        or user_input_data.at["user_data", "floorAreaRate"] != -1
    ):
        # 都市計画情報にユーザ入力がある場合で都市計画情報の開始年次あるいは終了年次の入力の有無を確認し、
        # ない場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "city_start_year"] == -1
            or user_input_data.at["user_data", "city_end_year"] == -1
        ):
            raise SenarioSettingException(
                "Error: 都市計画情報の値を変更する場合開始年次と終了年次を入力してください"
            )
        # 都市計画情報にユーザ入力がある場合で都市計画情報の開始年次がシナリオの開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "city_start_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 都市計画情報の開始年次はシナリオの開始年次以上の値を入力してください"
            )
        # 都市計画情報にユーザ入力がある場合で
        # 都市計画情報の終了年次がシナリオの終了年次より大きい場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "city_end_year"]
        ):
            raise SenarioSettingException(
                "Error: 都市計画情報の終了年次はシナリオの終了年次以下の値を入力してください"
            )
        # 都市計画情報にユーザ入力がある場合で
        # 都市計画情報の終了年次が都市計画情報の開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "city_end_year"]
            < user_input_data.at["user_data", "city_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 都市計画情報の終了年次は都市計画情報の開始年次以上の値を入力してください"
            )
    else:
        # 都市計画情報にユーザ入力がない場合で都市計画情報の開始年次あるいは終了年次がある場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "city_start_year"] != -1
            or user_input_data.at["user_data", "city_end_year"] != -1
        ):
            raise SenarioSettingException("Error: 都市計画情報の変更する値を入力してください")

    # 地価変更割合の開始年次と終了年次のユーザ入力のバリデーションチェック
    # 地価変更割合にユーザ入力があるか否かを確認する
    if (
        user_input_data.at["user_data", "ChangeRateCommercial"] != -1
        or user_input_data.at["user_data", "ChangeRateResidence"] != -1
    ):
        # 地価変更割合にユーザ入力がある場合で
        # 地価変更割合の開始年次あるいは終了年次の入力の有無を確認し、ない場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "land_start_year"] == -1
            or user_input_data.at["user_data", "land_end_year"] == -1
        ):
            raise SenarioSettingException(
                "Error: 地価変更割合の値を変更する場合開始年次と終了年次を入力してください"
            )
        # 地価変更割合にユーザ入力がある場合で地価変更割合の開始年次がシナリオの開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "land_start_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 地価変更割合の開始年次はシナリオの開始年次以上の値を入力してください"
            )
        # 地価変更割合にユーザ入力がある場合で
        # 地価変更割合の終了年次がシナリオの終了年次より大きい場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "land_end_year"]
        ):
            raise SenarioSettingException(
                "Error: 地価変更割合の終了年次はシナリオの終了年次以下の値を入力してください"
            )
        # 地価変更割合にユーザ入力がある場合で
        # 地価変更割合の終了年次が地価変更割合の開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "land_end_year"]
            < user_input_data.at["user_data", "land_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 地価変更割合の終了年次は地価変更割合の開始年次以上の値を入力してください"
            )
    else:
        # 地価変更割合にユーザ入力がない場合で地価変更割合の開始年次あるいは終了年次がある場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "land_start_year"] != -1
            or user_input_data.at["user_data", "land_end_year"] != -1
        ):
            raise SenarioSettingException("Error: 地価変更割合の変更する値を入力してください")

    # 転入転出割合の開始年次と終了年次のユーザ入力のバリデーションチェック
    # 転入転出割合にユーザ入力があるか否かを確認する
    if (
        user_input_data.at["user_data", "Migration_Rate_In"] != -1
        or user_input_data.at["user_data", "Migration_Rate_Out"] != -1
    ):
        # 転入転出割合にユーザ入力がある場合で
        # 転入転出割合の開始年次あるいは終了年次の入力の有無を確認し、ない場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "migration_start_year"] == -1
            or user_input_data.at["user_data", "migration_end_year"] == -1
        ):
            raise SenarioSettingException(
                "Error: 転入転出割合の値を変更する場合開始年次と終了年次を入力してください"
            )
        # 転入転出割合にユーザ入力がある場合で転入転出割合の開始年次がシナリオの開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "migration_start_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 転入転出割合の開始年次はシナリオの開始年次以上の値を入力してください"
            )
        # 転入転出割合にユーザ入力がある場合で
        # 転入転出割合の終了年次がシナリオの終了年次より大きい場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "migration_end_year"]
        ):
            raise SenarioSettingException(
                "Error: 転入転出割合の終了年次はシナリオの終了年次以下の値を入力してください"
            )
        # 転入転出割合にユーザ入力がある場合で
        # 転入転出割合の終了年次が転入転出割合の開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "migration_end_year"]
            < user_input_data.at["user_data", "migration_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 転入転出割合の終了年次は転入転出割合の開始年次以上の値を入力してください"
            )
    else:
        # 転入転出割合にユーザ入力がない場合で転入転出割合の開始年次あるいは終了年次がある場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "migration_start_year"] != -1
            or user_input_data.at["user_data", "migration_end_year"] != -1
        ):
            raise SenarioSettingException("Error: 転入転出割合の変更する値を入力してください")

    # 公共交通情報の開始年次と終了年次のユーザ入力のバリデーションチェック
    # 公共交通情報にユーザ入力があるか否かを確認する
    if (
        user_input_data.at["user_data", "Travel_Time_Rail"] != -1
        or user_input_data.at["user_data", "Waiting_Time_Rail"] != -1
        or user_input_data.at["user_data", "Access_Time_Rail"] != -1
        or user_input_data.at["user_data", "Egress_Time_Rail"] != -1
        or user_input_data.at["user_data", "Fare_Rail"] != -1
        or user_input_data.at["user_data", "Waiting_Time_Bus"] != -1
        or user_input_data.at["user_data", "Fare_Bus"] != -1
    ):
        # 公共交通情報にユーザ入力がある場合で
        # 公共交通情報の開始年次あるいは終了年次の入力の有無を確認し、ない場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "traffic_start_year"] == -1
            or user_input_data.at["user_data", "traffic_end_year"] == -1
        ):
            raise SenarioSettingException(
                "Error: 公共交通情報の値を変更する場合開始年次と終了年次を入力してください"
            )
        # 公共交通情報にユーザ入力がある場合で
        # 公共交通情報の開始年次がシナリオの開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "traffic_start_year"]
            < user_input_data.at["user_data", "scenario_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 公共交通情報の開始年次はシナリオの開始年次以上の値を入力してください"
            )
        # 公共交通情報にユーザ入力がある場合で
        # 公共交通情報の終了年次がシナリオの終了年次より大きい場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "scenario_end_year"]
            < user_input_data.at["user_data", "traffic_end_year"]
        ):
            raise SenarioSettingException(
                "Error: 公共交通情報の終了年次はシナリオの終了年次以下の値を入力してください"
            )
        # 公共交通情報にユーザ入力がある場合で
        # 公共交通情報の終了年次が公共交通情報の開始年次未満の場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "traffic_end_year"]
            < user_input_data.at["user_data", "traffic_start_year"]
        ):
            raise SenarioSettingException(
                "Error: 公共交通情報の終了年次は公共交通情報の開始年次以上の値を入力してください"
            )
    else:
        # 公共交通情報にユーザ入力がない場合で公共交通情報の開始年次あるいは終了年次がある場合はエラー処理を行う
        if (
            user_input_data.at["user_data", "traffic_start_year"] != -1
            or user_input_data.at["user_data", "traffic_end_year"] != -1
        ):
            raise SenarioSettingException("Error: 公共交通情報の変更する値を入力してください")

    # 処理成功時の返値
    return user_input_data


def get_set_zone(user_input_data, directory_and_file_path):
    """
    ゾーンデータの読込を行う、読込時に以降処理で使用するフィールドの追加とバリデーションチェックを行い、ゾーン特定を行う
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    ファイル出力
        ゾーンデータ(メモリ上)
    """
    # ゾーンデータのファイル存在確認を行う
    if not (arcpy.Exists(directory_and_file_path["zone_data_path"])):
        raise SenarioSettingException(
            "Error: Zone(geodatabase)が存在しないため終了します\n{}".format(
                directory_and_file_path["zone_data_path"]
            )
        )

    # [geodatabaseをメモリ上にエクスポートする]
    # ゾーンデータを中間ファイルとしてメモリ上にエクスポートする
    zone_data_path = get_reference_data(
        user_input_data, directory_and_file_path, "Zone"
    )[0]
    arcpy.conversion.ExportTable(
        in_table=zone_data_path,
        out_table=ZONE_DATA_TMP,
        field_mapping=(
            'zone_code "zone_code" '
            "true true false 8000 Text 0 0,First,#,"
            f"{zone_data_path}"
            ",zone_code,-1,-1;"
            'AREA "AREA" '
            "true true false 8 Double 0 0,First,#,"
            f"{zone_data_path}"
            ",AREA,-1,-1;"
            'Avg_Dist_sta_centre "Avg_Dist_sta_centre"'
            "true true false 8 Double 0 0,First,#,"
            f"{zone_data_path}"
            ",Avg_Dist_sta_centre,-1,-1;"
            'Avg_Dist_sta_main "Avg_Dist_sta_main" '
            "true true false 8 Double 0 0,First,#,"
            f"{zone_data_path}"
            ",Avg_Dist_sta_main,-1,-1;"
            'Avg_Dist_sta_other "Avg_Dist_sta_other" '
            "true true false 8 Double 0 0,First,#,"
            f"{zone_data_path}"
            ",Avg_Dist_sta_other,-1,-1;"
            'UseDistrict "UseDistrict" '
            "true true false 8 Text 0 0,First,#,"
            f"{zone_data_path}"
            ",UseDistrict,-1,-1;"
            'floorAreaRate "floorAreaRate" '
            "true true false 8 Long 0 0,First,#,"
            f"{zone_data_path}"
            ",floorAreaRate,-1,-1;"
            'buildingCoverageRate "buildingCoverageRate" '
            "true true false 8 Long 0 0,First,#,"
            f"{zone_data_path}"
            ",buildingCoverageRate,-1,-1"
        ),
    )

    # 中間ファイルのゾーンデータにフィールドを追加する
    add_field_zone_data(
        user_input_data, directory_and_file_path, ZONE_DATA_TMP
    )

    # [ゾーンデータのバリデーションチェック]
    # geodatabaseからソート用のOBJECTIDとゾーンコードのデータをnumpy型で抽出する
    zone_code_list_zone_data = [
        list(row)
        for row in arcpy.da.FeatureClassToNumPyArray(
            ZONE_DATA_TMP, ["OBJECTID", "zone_code"]
        )
    ]
    # OBJECTIDでソートする
    zone_code_list_zone_data = sorted(
        zone_code_list_zone_data, key=lambda x: x[0]
    )
    # OBJECTIDはソート後不要のため削除する
    zone_code_list_zone_data = np.delete(
        zone_code_list_zone_data, slice(0, 1), axis=1
    )

    # ゾーンデータに対してゾーンコードの重複確認を行う
    # ゾーンデータのゾーンコードの列リストにユーザ入力のソースコードが複数あるかチェックし、
    # あれば列のインデックスを特定し、メッセージに出力する
    for zone_code in user_input_data.at["user_data", "zone_code"]:
        if np.count_nonzero(zone_code_list_zone_data == zone_code) > 1:
            # ゾーンデータのゾーンコードの列リストからユーザ入力のゾーンコードの列インデックスをリストに格納する
            dup_zone_code_zone_data = [
                i
                for i, zone_code_index in enumerate(zone_code_list_zone_data)
                if zone_code_index == zone_code
            ]
            # pythonのリストは0から始まるためindexに1を加算する
            dup_zone_code_zone_data = [n + 1 for n in dup_zone_code_zone_data]
            raise SenarioSettingException(
                (
                    f"Error: Zone(geodatabase)に入力されたゾーンコード{zone_code}は"
                    "{dup_zone_code_zone_data}行目 が重複しているため終了します"
                )
            )

        # ゾーンデータのゾーン特定を行う
        identification_zone_code(
            zone_code,
            zone_code_list_zone_data,
        )


def get_zone_codes(path: str):
    res = []
    with arcpy.da.SearchCursor(path, "zone_code") as Cursor:
        res = [row[0] for row in Cursor]
    del Cursor
    return res


def verify_building(user_input_data, building_data_path: str):
    """
    建築物データのファイル存在確認とゾーン特定を行う。
    建築物データはシナリオ設定UI機能で出力を行わないためファイルの存在確認とゾーン特定のみ行う
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし
    """
    # 建築物データのファイル存在確認を行う
    if not (arcpy.Exists(building_data_path)):
        raise SenarioSettingException(
            "Error: Building(gaodatabase)が存在しないため終了します\n{}".format(
                building_data_path
            )
        )

    # [建築物データのバリデーションチェック]
    # geodatabaseからゾーンコードのデータをリスト型で抽出する
    zone_code_list_building_data = get_zone_codes(building_data_path)

    # 建築物データのゾーン特定を行う
    for zone_code in user_input_data.at["user_data", "zone_code"]:
        identification_zone_code(
            zone_code,
            zone_code_list_building_data,
        )


def identification_zone_code(zone_code, zone_code_list):
    """
    ゾーンの特定を行う
    [UC23-07_IBSKKC_都市構造シミュレーション_要件定義資料_v0.2_レビュー後加筆v01.docx p25 ゾーン特定]
    引数；
        zone_code[String型]:ゾーンコード
        zone_code_list[list型]:ゾーンデータ/建築物データ
    返値:
        なし
    """
    # geodatabaseのゾーンコードの列のリストにユーザ入力のゾーンコードが含まれるか確認し、含まれない場合エラー処理を行う
    if not (zone_code in zone_code_list):
        raise SenarioSettingException(
            "Error: Zone(geodatabase)に入力されたゾーンコード {} が存在しないため終了します".format(
                zone_code
            )
        )


def get_zone_traveltime(user_input_data, directory_and_file_path):
    """
    ゾーン間所用時間データの読込と読込時にバリデーションチェックを行い、対象データの特定を行う
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        zone_traveltime_data[データフレーム型]:ゾーン間所要時間データ
    """

    # ゾーン間所用時間設定データのファイル存在確認を行う
    if not (os.path.isfile(directory_and_file_path["zone_traveltime_path"])):
        raise SenarioSettingException(
            "Error: Zone_TravelTime.csvが存在しないため終了します\n{}".format(
                directory_and_file_path["zone_traveltime_path"]
            )
        )

    # ゾーン間所用時間設定のCSVをデータフレーム型の変数に格納する。
    zone_traveltime_data = pd.read_csv(
        get_reference_data(
            user_input_data, directory_and_file_path, "Zone_TravelTime"
        )[0],
        dtype={
            "zone_code_o": "str",
            "zone_code_d": "str",
            "Travel_Time_Rail": "float",
            "Waiting_Time_Rail": "float",
            "Access_Time_Rail": "float",
            "Egress_Time_Rail": "float",
            "Fare_Rail": "float",
            "Travel_Time_Bus": "float",
            "Waiting_Time_Bus": "float",
            "Access_Time_Bus": "float",
            "Egress_Time_Bus": "float",
            "Fare_Bus": "float",
            "Travel_Time_Car": "float",
        },
        header=0,
        encoding="shift_jis",
    )

    # ゾーン間所用時間設定の対象データの特定を行う
    for zone_code in user_input_data.at["user_data", "zone_code"]:
        if not has_zone_code(
            zone_code,
            zone_traveltime_data,
            "zone_code_o",
        ) or not has_zone_code(
            zone_code,
            zone_traveltime_data,
            "zone_code_d",
        ):
            raise SenarioSettingException(
                (
                    "Error: Zone_TravelTime.csvに入力されたゾーンコード"
                    f"{zone_code} が存在しないため終了します"
                )
            )

    # 処理成功時の返値
    return zone_traveltime_data


def get_facility_num(user_input_data, directory_and_file_path):
    """
    施設数データの読込と読込時にバリデーションチェックを行い、対象データの特定を行う
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        zone_facility_num_data[データフレーム型]:施設数データ
    """
    # 施設数データのファイル存在確認を行う
    if not (
        os.path.isfile(directory_and_file_path["zone_facility_num_data_path"])
    ):
        raise SenarioSettingException(
            "Error: Zone_FacilityNum.csvが存在しないため終了します\n{}".format(
                directory_and_file_path["zone_facility_num_data_path"]
            )
        )

    # 開始年次以下のファイルが存在する場合はZone_FacilityNum_年次のCSVファイルを元にする
    # 施設数データのCSVをデータフレーム型の変数に格納する。
    zone_facility_num_data = pd.read_csv(
        get_reference_data(
            user_input_data, directory_and_file_path, "Zone_FacilityNum"
        )[0],
        dtype={
            "zone_code": "str",
            "fnum_Library": "int",
            "fnum_Hospital": "int",
            "fnum_Clinic": "int",
            "fnum_ElementarySchool": "int",
            "fnum_MiddleSchool": "int",
            "fnum_PreSchool": "int",
        },
        header=0,
        encoding="shift_jis",
    )

    # [施設数データのバリデーションチェック]
    # 施設数データのゾーンコードの重複確認をする
    # ユーザ入力のゾーンコードが複数あるかチェックし、あれば列のインデックスを特定し、メッセージに出力する
    for zone_code in user_input_data.at["user_data", "zone_code"]:
        if (
            zone_facility_num_data.loc[:, "zone_code"]
            .to_list()
            .count(zone_code)
            > 1
        ):
            # ゾーンデータのゾーンコードの列リストからユーザ入力のゾーンコードの列インデックスをリストに格納する
            dup_zone_code_facility_num_data = [
                i
                for i, zone_code_index in enumerate(
                    zone_facility_num_data.loc[:, "zone_code"].to_list()
                )
                if zone_code_index == zone_code
            ]

            # pythonのリストは0から始まるためindexに1を加算する
            dup_zone_code_facility_num_data = [
                n + 1 for n in dup_zone_code_facility_num_data
            ]
            raise SenarioSettingException(
                (
                    f"Error: Zone_FacilityNum.csvに入力されたゾーンコード {zone_code}は"
                    f"{dup_zone_code_facility_num_data}行目 が重複しているため終了します"
                )
            )

        # 施設数データのゾーンコードの存在確認をする
        if not has_zone_code(
            zone_code,
            zone_facility_num_data,
            "zone_code",
        ):
            raise SenarioSettingException(
                (
                    f"Error: Zone_FacilityNum.csvに入力されたゾーンコード"
                    f"{zone_code} が存在しないため終了します"
                )
            )

    # 処理成功時の返値
    return zone_facility_num_data


def add_field_zone_data(
    user_input_data, directory_and_file_path, zone_data_tmp
):
    """
    中間ファイルのゾーンデータにフィールドを追加する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        zone_data_tmp[テーブル]:ゾーンデータの中間ファイル
    返値:
        なし
    """
    # Land_Price_Change_Rate
    # 商業地価割引率
    arcpy.management.CalculateField(
        zone_data_tmp,
        "ChangeRateCommercial",
        "0",
        expression_type="PYTHON3",
        field_type="LONG",
    )
    # 住宅地価割引率
    arcpy.management.CalculateField(
        zone_data_tmp,
        "ChangeRateResidence",
        "0",
        expression_type="PYTHON3",
        field_type="LONG",
    )
    # 過去年次のデータが存在する場合は上書きする
    land_price_change_rate_path, exist_flag = get_reference_data(
        user_input_data, directory_and_file_path, "Land_Price_Change_Rate"
    )
    if exist_flag:
        land_price_change_rate_data = pd.read_csv(
            land_price_change_rate_path,
            index_col=0,
            encoding="shift_jis",
        )
        with arcpy.da.UpdateCursor(
            zone_data_tmp,
            ["zone_code", "ChangeRateCommercial", "ChangeRateResidence"],
        ) as uCusor:
            for row in uCusor:
                data_tmp = land_price_change_rate_data.loc[int(row[0])]
                if data_tmp.empty:
                    continue
                row[1] = data_tmp.at["ChangeRateCommercial"]
                row[2] = data_tmp.at["ChangeRateResidence"]
                uCusor.updateRow(row)
        del uCusor


def get_reference_data(user_input_data, directory_and_file_path, field):
    """
    元データのファイルパスを取得する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        field[String型]:Control_SimInput.csvのフィールド名
    返値:
        file_path[String型]:更新対象のファイルパス
        exist_flag[bool型]:過去ファイルの存在フラグ
    """
    # 各ファイルのパスを取得するためのキー名と開始年次のキー名を取得
    path_key = ""
    start_year_key = ""
    if field == "Zone":
        path_key = "zone_data_path"
        start_year_key = "city_start_year"
    elif field == "Zone_FacilityNum":
        path_key = "zone_facility_num_data_path"
        start_year_key = "facility_start_year"
    elif field == "Zone_TravelTime":
        path_key = "zone_traveltime_path"
        start_year_key = "traffic_start_year"
    elif field == "Land_Price_Change_Rate":
        path_key = "land_price_change_rate_path"
        start_year_key = "land_start_year"
    elif field == "Migration_Rate":
        path_key = "migration_rate_path"
        start_year_key = "migration_start_year"
    # Control_SimInput.csvの情報と比較してファイルパスの設定
    file_path = directory_and_file_path[path_key]
    if os.path.isfile(directory_and_file_path["control_siminput_data_path"]):
        path_series = pd.read_csv(
            directory_and_file_path["control_siminput_data_path"],
            encoding="shift_jis",
        )[field]
        path_series = path_series.sort_values(
            ascending=False
        ).drop_duplicates()
        for path_tmp in path_series:
            # ファイル名に年次がついていない場合は次のファイルを確認
            if directory_and_file_path[path_key] == path_tmp:
                continue
            file_year = int(
                os.path.splitext(os.path.basename(path_tmp))[0].split("_")[-1]
            )
            if user_input_data.at["user_data", start_year_key] >= file_year:
                file_path = path_tmp
                break
        return file_path, True
    else:
        return file_path, False


def has_zone_code(zone_code, csv_data, field_name):
    """
    対象データの特定を行う
    [UC23-07_IBSKKC_都市構造シミュレーション_要件定義資料_v0.2_レビュー後加筆v01.docx p26 対象データ特定]
    引数:
        zone_code[String型]:ゾーンコード
        csv_data[データフレーム型]:ゾーン間所要時間データ/施設数データ
        field_name[String型]:csvデータのゾーンコードに対応するフィールド名
    返値:
        なし
    """
    # csvファイルのゾーンコードの列のリストにユーザ入力のゾーンコードが含まれるか確認し、含まれない場合エラー処理を行う
    return zone_code in csv_data.loc[:, field_name].values


def get_set_siminput(user_input_data, directory_and_file_path):
    """
    Control_SimInputデータの初期値を作成する。
    Contorl_SimInputファイルの存在確認し、存在していればデータの読込し、初期値データを読込したデータの下に
    垂直にマージしyearをキーに上から1つ目を優先して重複削除を行う
    引数:
        user_input_data[データフレーム型]:ユーザ入力を格納したデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        control_siminput_data[データフレーム型]:control_siminputデータ

    """
    control_siminput_data_columns = [
        "year",
        "Zone",
        "Zone_FacilityNum",
        "Dist_Zone_Facility",
        "Zone_TravelTime",
        "Dist_Building_Station",
        "Land_Price_Change_Rate",
        "Migration_Rate",
    ]

    if os.path.isfile(directory_and_file_path["control_siminput_data_path"]):
        # Control_SimInput.csv が存在する場合はこれを読み込む
        return pd.read_csv(
            directory_and_file_path["control_siminput_data_path"],
            usecols=control_siminput_data_columns,
            dtype={
                "year": "int",
                "Zone": "str",
                "Zone_FacilityNum": "str",
                "Dist_Zone_Facility": "str",
                "Zone_TravelTime": "str",
                "Dist_Building_Station": "str",
                "Land_Price_Change_Rate": "str",
                "Migration_Rate": "str",
            },
            encoding="shift_jis",
        )
    # Control_SimInput.csv が存在しない場合は初期値データを作成する
    control_siminput_default = [
        [
            year_count,
            directory_and_file_path["zone_data_path"],
            directory_and_file_path["zone_facility_num_data_path"],
            directory_and_file_path["dist_zone_facility_path"],
            directory_and_file_path["zone_traveltime_path"],
            directory_and_file_path["dist_building_station_path"],
            directory_and_file_path["land_price_change_rate_path"],
            directory_and_file_path["migration_rate_path"],
        ]
        for year_count in range(
            user_input_data.at["user_data", "scenario_start_year"],
            user_input_data.at["user_data", "scenario_end_year"] + 1,
        )
    ]
    return pd.DataFrame(
        control_siminput_default, columns=control_siminput_data_columns
    )


def get_set_simyear(user_input_data, directory_and_file_path):
    """
    Control_SimYearデータの存在確認を行い、存在していない場合新たにデータを作成し、存在している場合読み込む
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        control_simyear_data[list型]:control_simyearデータ
    """
    # Control_SimYear.csvの存在確認を行う。ない場合データの作成、ある場合データの読込みを行う
    if not os.path.isfile(
        directory_and_file_path["control_simyear_data_path"]
    ):
        # control_simyearデータ作成
        return [
            user_input_data.at["user_data", "scenario_start_year"],
            user_input_data.at["user_data", "scenario_end_year"],
        ]
    # control_simyearデータの読込
    with open(
        directory_and_file_path["control_simyear_data_path"],
        encoding="shift_jis",
    ) as f:
        return list(map(int, f.readlines()))


def get_file_dict(in_data: pd.DataFrame, root: str=PROJECT_ROOT_PATH):
    sim_dir = rf"{root}\Simulation"
    base_data_dir = rf"{sim_dir}\BaseData"
    scenario_dir = (
        rf"{sim_dir}\Scenario" rf'\{in_data.at["user_data", "scenario_name"]}'
    )
    return {
        "zone_data_path": rf"{base_data_dir}\Zone.csv",
        "building_data_path": rf"{base_data_dir}\BaseData.gdb\Building",
        "zone_traveltime_path": rf"{base_data_dir}\Zone_TravelTime.csv",
        "zone_facility_num_data_path": (
            rf"{base_data_dir}\Zone_FacilityNum.csv"
        ),
        "output_directory_path": scenario_dir,
        "basedata_path": base_data_dir,
        "sim_output_path": (
            rf'{root}\Output\{in_data.at["user_data", "scenario_name"]}'
        ),
        "control_siminput_data_path": rf"{scenario_dir}\Control_SimInput.csv",
        "control_simyear_data_path": rf"{scenario_dir}\Control_SimYear.txt",
        "control_sim_data_path": rf"{scenario_dir}\Control_Sim.txt",
        "dist_zone_facility_path": rf"{base_data_dir}\Dist_Zone_Facility.csv",
        "dist_building_station_path": (
            rf"{base_data_dir}\Dist_Building_Station.csv"
        ),
        "land_price_change_rate_path": (
            rf"{scenario_dir}\Land_Price_Change_Rate.csv"
        ),
        "migration_rate_path": rf"{scenario_dir}\Migration_Rate.csv",
        "output_zone_path": (
            rf"{scenario_dir}\Zone_"
            rf'{in_data.at["user_data", "city_start_year"]}.csv'
        ),
        "output_zone_traveltime_path": (
            rf"{scenario_dir}\Zone_TravelTime_"
            rf'{in_data.at["user_data", "traffic_start_year"]}.csv'
        ),
        "output_land_rate_path": (
            rf"{scenario_dir}\Land_Price_Change_Rate_"
            rf'{in_data.at["user_data", "land_start_year"]}.csv'
        ),
        "output_migration_rate_path": (
            rf"{scenario_dir}\Migration_Rate_"
            rf'{in_data.at["user_data", "migration_start_year"]}.csv'
        ),
        "output_zone_facility_num_path": (
            rf"{scenario_dir}\Zone_FacilityNum_"
            rf'{in_data.at["user_data", "facility_start_year"]}.csv'
        ),
        "control_sim_txt_path": rf"{sim_dir}\Control_Sim.txt",
    }


def input_preprocessing(user_input_data: pd.DataFrame):
    """
    geodatabaseとcsvファイルの入力データ(現況)の存在確認と読込を行い、入力データのバリデーションチェックを行う。
    geodatabaseのゾーンデータはメモリ上に読込した後にフィールドを追加する。
    建築物データはバリデーションチェックのみ行う。
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
    返値:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        Zone_TravelTime_data[データフレーム型]:ゾーン間所用時間データ
        zone_facility_num_data[データフレーム型]:施設数データ
        control_siminput_data[データフレーム型]:control_siminputデータ
        control_simyear_data[list型]:control_simyearデータ

    ファイル入力:
        Zone:ゾーンデータのgeodatabase
        Building:建築物データのgeodatabase
        Zone_TravelTime.csv:ゾーン間所要時間データ
        Zone_FacilityNum.csv:施設数データ
        Control_SimInput.csv:control_siminputデータ
        Control_SimYear.csv:control_simyearデータ
    ファイル出力:
        ゾーンデータ(メモリ上)
    """

    logger = set_log_format("input_preprocessing")
    logger.info("Start processing.")
    # ファイルとフォルダの絶対パスを格納する
    # 絶対パス設定
    directory_and_file_path = pd.Series(dtype=str).append(
        pd.Series(get_file_dict(user_input_data))
    )

    # ゾーンデータの更新用データ作成処理
    get_set_zone(user_input_data, directory_and_file_path)

    # 建築物データの存在確認とバリデーションチェック
    verify_building(
        user_input_data, directory_and_file_path["building_data_path"]
    )

    # ゾーン間所用時間設定データの更新用データ作成処理
    zone_traveltime_data = get_zone_traveltime(
        user_input_data, directory_and_file_path
    )

    # 施設数データの更新用データ作成処理
    zone_facility_num_data = get_facility_num(
        user_input_data, directory_and_file_path
    )

    # Control_SimInputデータの更新用データ作成処理
    control_siminput_data = get_set_siminput(
        user_input_data, directory_and_file_path
    )

    # Control_SimYearデータの更新用データ作成処理
    control_simyear_data = get_set_simyear(
        user_input_data, directory_and_file_path
    )

    logger.info("Complete processing.")

    # 処理成功時の返値
    return (
        directory_and_file_path,
        zone_traveltime_data,
        zone_facility_num_data,
        control_siminput_data,
        control_simyear_data,
    )


def update_zone_setting_info(user_input_data, zone_facility_num_data):
    """
    ゾーンコードをキーとしてユーザ入力の値をゾーンデータや施設数データの値に更新し、
    返値としてユーザ入力反映後の施設数データを返す。
    入力値が-1の場合は上書きしない。
    引数：
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        zone_facility_num_data[データフレーム型]:施設数データ
    返値:
        zone_facility_num_data[データフレーム型]:施設数データ

    入力ファイル:
        ゾーンデータ(メモリ上)
    出力ファイル:
        ゾーンデータ(メモリ上)
    """
    # ゾーンデータ更新
    # [都市計画情報の更新]
    # 容積率の更新

    logger = set_log_format("update_zone_setting_info")
    logger.info("Start processing.")

    if user_input_data.at["user_data", "floorAreaRate"] != -1:
        with arcpy.da.UpdateCursor(
            ZONE_DATA_TMP, ["zone_code", "floorAreaRate"]
        ) as uCusor:
            for row in uCusor:
                if row[0] in user_input_data.at["user_data", "zone_code"]:
                    row[1] = user_input_data.at["user_data", "floorAreaRate"]
                    uCusor.updateRow(row)
        del uCusor

    # 用途地域の更新
    if user_input_data.at["user_data", "UseDistrict"] != "":
        with arcpy.da.UpdateCursor(
            ZONE_DATA_TMP, ["zone_code", "UseDistrict"]
        ) as uCusor:
            for row in uCusor:
                if row[0] in user_input_data.at["user_data", "zone_code"]:
                    row[1] = user_input_data.at["user_data", "UseDistrict"]
                    uCusor.updateRow(row)
        del uCusor

    # [地価変更割合の更新]
    # 商業地価変更割合の更新
    if user_input_data.at["user_data", "ChangeRateCommercial"] != -1:
        with arcpy.da.UpdateCursor(
            ZONE_DATA_TMP, ["zone_code", "ChangeRateCommercial"]
        ) as uCusor:
            for row in uCusor:
                if row[0] in user_input_data.at["user_data", "zone_code"]:
                    row[1] = user_input_data.at[
                        "user_data", "ChangeRateCommercial"
                    ]
                    uCusor.updateRow(row)
        del uCusor

    # 商業地価変更割合の更新
    if user_input_data.at["user_data", "ChangeRateResidence"] != -1:
        with arcpy.da.UpdateCursor(
            ZONE_DATA_TMP, ["zone_code", "ChangeRateResidence"]
        ) as uCusor:
            for row in uCusor:
                if row[0] in user_input_data.at["user_data", "zone_code"]:
                    row[1] = user_input_data.at[
                        "user_data", "ChangeRateResidence"
                    ]
                    uCusor.updateRow(row)
        del uCusor

    # [施設数データを更新する]
    # [施設数の更新]
    # 図書館の更新
    for zone_code in user_input_data.at["user_data", "zone_code"]:
        if user_input_data.at["user_data", "fnum_Library"] != -1:
            zone_facility_num_data.loc[
                zone_facility_num_data["zone_code"] == zone_code,
                ["fnum_Library"],
            ] = user_input_data.at["user_data", "fnum_Library"]

        # 病院の更新
        if user_input_data.at["user_data", "fnum_Hospital"] != -1:
            zone_facility_num_data.loc[
                zone_facility_num_data["zone_code"] == zone_code,
                ["fnum_Hospital"],
            ] = user_input_data.at["user_data", "fnum_Hospital"]

        # 小学校の更新
        if user_input_data.at["user_data", "fnum_ElementarySchool"] != -1:
            zone_facility_num_data.loc[
                zone_facility_num_data["zone_code"] == zone_code,
                ["fnum_ElementarySchool"],
            ] = user_input_data.at["user_data", "fnum_ElementarySchool"]

        # 中学校の更新
        if user_input_data.at["user_data", "fnum_MiddleSchool"] != -1:
            zone_facility_num_data.loc[
                zone_facility_num_data["zone_code"] == zone_code,
                ["fnum_MiddleSchool"],
            ] = user_input_data.at["user_data", "fnum_MiddleSchool"]

        # 幼稚園及びこども園の更新
        if user_input_data.at["user_data", "fnum_PreSchool"] != -1:
            zone_facility_num_data.loc[
                zone_facility_num_data["zone_code"] == zone_code,
                ["fnum_PreSchool"],
            ] = user_input_data.at["user_data", "fnum_PreSchool"]

    logger.info("Complete processing.")

    # 処理成功時の返値
    return zone_facility_num_data


def update_zone_traveltime(user_input_data, zone_traveltime_data):
    """
    ゾーンコードをキーとしてユーザ入力の値をゾーン間所用時間データの値に更新し、
    ユーザ入力反映後のゾーン間所用時間設定データを返す
    入力値が-1の場合は上書きしない。
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        zone_traveltime_data[データフレーム型]:ゾーン間所要時間データ
    返値:
        zone_traveltime_data[データフレーム型]:ゾーン間所要時間データ
    """
    # [手段別時間変更割合の更新]
    # 鉄道乗車時間の更新

    logger = set_log_format("update_zone_traveltime")
    logger.info("Start processing.")

    # 更新対象取得
    update_target = zone_traveltime_data.loc[
        (
            zone_traveltime_data["zone_code_o"].isin(
                user_input_data.at["user_data", "zone_code"]
            )
        )
        & (
            zone_traveltime_data["zone_code_d"].isin(
                user_input_data.at["user_data", "zone_code"]
            )
        )
    ]

    # 鉄道乗者時間の更新
    if user_input_data.at["user_data", "Travel_Time_Rail"] != -1:
        update_target["Travel_Time_Rail"] *= (
            user_input_data.at["user_data", "Travel_Time_Rail"] / 100
        )

    # 鉄道待ち時間の更新
    if user_input_data.at["user_data", "Waiting_Time_Rail"] != -1:
        update_target["Waiting_Time_Rail"] *= (
            user_input_data.at["user_data", "Waiting_Time_Rail"] / 100
        )

    # 鉄道アクセス時間の更新
    if user_input_data.at["user_data", "Access_Time_Rail"] != -1:
        update_target["Access_Time_Rail"] *= (
            user_input_data.at["user_data", "Access_Time_Rail"] / 100
        )

    # 鉄道イグレス時間の更新
    if user_input_data.at["user_data", "Egress_Time_Rail"] != -1:
        update_target["Egress_Time_Rail"] *= (
            user_input_data.at["user_data", "Egress_Time_Rail"] / 100
        )

    # 鉄道運賃の更新
    if user_input_data.at["user_data", "Fare_Rail"] != -1:
        update_target["Fare_Rail"] *= (
            user_input_data.at["user_data", "Fare_Rail"] / 100
        )

    # バス待ち時間の更新
    if user_input_data.at["user_data", "Waiting_Time_Bus"] != -1:
        update_target["Waiting_Time_Bus"] *= (
            user_input_data.at["user_data", "Waiting_Time_Bus"] / 100
        )

    # バス運賃の更新
    if user_input_data.at["user_data", "Fare_Bus"] != -1:
        update_target["Fare_Bus"] *= (
            user_input_data.at["user_data", "Fare_Bus"] / 100
        )

    # 元のデータ更新
    zone_traveltime_data.loc[
        (
            zone_traveltime_data["zone_code_o"].isin(
                user_input_data.at["user_data", "zone_code"]
            )
        )
        & (
            zone_traveltime_data["zone_code_d"].isin(
                user_input_data.at["user_data", "zone_code"]
            )
        )
    ] = update_target

    logger.info("Complete processing.")

    # 処理成功時の返値
    return zone_traveltime_data


def update_control_simyear(user_input_data, control_simyear_data):
    """
    control_simyearデータを更新する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        control_simyear_data[list型]:control_simyearデータ
    返値:
        control_simyear_data[list型]:control_simyearデータ
    """

    logger = set_log_format("update_control_simyear")
    logger.info("Start processing.")

    # control_simyearの開始年次よりシナリオの開始年次の値が大きい場合値を更新する
    if (
        user_input_data.at["user_data", "scenario_start_year"]
        < control_simyear_data[0]
    ):
        control_simyear_data[0] = user_input_data.at[
            "user_data", "scenario_start_year"
        ]

    # control_simyearの終了年次がシナリオの終了年次の値より小さい場合値を更新する
    if (
        control_simyear_data[1]
        < user_input_data.at["user_data", "scenario_end_year"]
    ):
        control_simyear_data[1] = user_input_data.at[
            "user_data", "scenario_end_year"
        ]

    logger.info("Complete processing.")

    # 処理成功時の返値
    return control_simyear_data


def update_control_siminput(
    user_input_data, directory_and_file_path, control_siminput_data
):
    """
    control_siminputデータを更新する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        control_siminput_data[list型]:control_siminputデータ
    返値:
        control_siminput_data[list型]:control_siminputデータ
    """

    logger = set_log_format("set_symbol_layer")
    logger.info("Start processing.")

    # 都市情報の開始年次から終了年次までのZoneの絶対パスを更新する
    control_siminput_data.loc[
        (
            control_siminput_data["year"]
            >= user_input_data.at["user_data", "city_start_year"]
        )
        & (
            control_siminput_data["year"]
            <= user_input_data.at["user_data", "city_end_year"]
        ),
        "Zone",
    ] = directory_and_file_path["output_zone_path"]

    # 公共交通情報の開始年次から終了年次までのZone_TravelTimeの絶対パスを更新する
    control_siminput_data.loc[
        (
            control_siminput_data["year"]
            >= user_input_data.at["user_data", "traffic_start_year"]
        )
        & (
            control_siminput_data["year"]
            <= user_input_data.at["user_data", "traffic_end_year"]
        ),
        "Zone_TravelTime",
    ] = directory_and_file_path["output_zone_traveltime_path"]

    # 地価変更割合の開始年次から終了年次までのLand_Price_Change_Rateの絶対パスを更新する
    control_siminput_data.loc[
        (
            control_siminput_data["year"]
            >= user_input_data.at["user_data", "land_start_year"]
        )
        & (
            control_siminput_data["year"]
            <= user_input_data.at["user_data", "land_end_year"]
        ),
        "Land_Price_Change_Rate",
    ] = directory_and_file_path["output_land_rate_path"]

    # 転入転出割合の開始年次から終了年次までのMigration_Rateの絶対パスを更新する
    control_siminput_data.loc[
        (
            control_siminput_data["year"]
            >= user_input_data.at["user_data", "migration_start_year"]
        )
        & (
            control_siminput_data["year"]
            <= user_input_data.at["user_data", "migration_end_year"]
        ),
        "Migration_Rate",
    ] = directory_and_file_path["output_migration_rate_path"]

    # 施設数情報の開始年次から終了年次までのZone_FacilityNumの絶対パスを更新する
    control_siminput_data.loc[
        (
            control_siminput_data["year"]
            >= user_input_data.at["user_data", "facility_start_year"]
        )
        & (
            control_siminput_data["year"]
            <= user_input_data.at["user_data", "facility_end_year"]
        ),
        "Zone_FacilityNum",
    ] = directory_and_file_path["output_zone_facility_num_path"]

    logger.info("Complete processing.")

    # 処理成功時の返値
    return control_siminput_data


def check_and_make_directory(directory_and_file_path):
    """
    シナリオファイルと都市構造シミュレーション機能の出力フォルダの存在確認を行い、ない場合は作成を行う
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    フォルダ出力:
        (フォルダがない場合)シナリオファイルの出力フォルダ,都市構造シミュレーション機能の出力フォルダ
    """
    # シナリオの名前から出力フォルダの存在確認を行い、フォルダがなければ作成する
    if not os.path.isdir(directory_and_file_path["output_directory_path"]):
        os.mkdir(directory_and_file_path["output_directory_path"])

    # 都市構造シミュレーション機能の出力フォルダの存在確認を行い、フォルダがなければ作成する
    if not os.path.isdir(directory_and_file_path["sim_output_path"]):
        os.mkdir(directory_and_file_path["sim_output_path"])


def output_csv_zone(directory_and_file_path):
    """
    シナリオゾーンデータのcsvを出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    ファイル入力:
        ゾーンデータ(メモリ上)
    ファイル出力:
        Zone_[都市情報の開始年次].csv

    """
    zone_fields = [
        "zone_code",
        "AREA",
        "Avg_Dist_sta_centre",
        "Avg_Dist_sta_main",
        "Avg_Dist_sta_other",
        "UseDistrict",
        "floorAreaRate",
        "buildingCoverageRate",
    ]

    # ゾーンデータをcsvで出力するためにgeodatabaseからデータを抽出する
    numpy_zone_data = [
        list(row)
        for row in arcpy.da.FeatureClassToNumPyArray(
            ZONE_DATA_TMP, ["OBJECTID", zone_fields]
        )
    ]

    # OBJECTIDでソートする
    numpy_zone_data = sorted(numpy_zone_data, key=lambda x: x[0])

    # OBJECTIDは出力しないため削除する
    numpy_zone_data = np.delete(numpy_zone_data, slice(0, 1), axis=1)

    # シナリオゾーンデータを出力する
    with open(
        directory_and_file_path["output_zone_path"],
        "w",
        encoding="shift_jis",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(zone_fields)
        writer.writerows(numpy_zone_data)


def output_csv_facility_num(directory_and_file_path, zone_facility_num_data):
    """
    シナリオ施設数データのcsvを出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        zone_facility_num_data[データフレーム型]:施設数データ
    返値:
        なし

    ファイル入力:
        ゾーンデータ(メモリ上)
    ファイル出力:
        Zone_FacilityNum_[施設数の開始年次].csv
    """
    # シナリオ施設数データを出力する
    zone_facility_num_data.to_csv(
        directory_and_file_path["output_zone_facility_num_path"],
        index=False,
        line_terminator="",
        encoding="shift_jis",
    )


def output_csv_zone_traveltime(directory_and_file_path, zone_traveltime_data):
    """
    シナリオゾーン間所用時間設定データのcsvを出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        zone_traveltime_data[データフレーム型]:ゾーン間所要時間データ
    返値:
        なし

    ファイル出力:
        Zone_TravelTime_[公共交通情報の開始年次].csv
    """
    # シナリオゾーン間所用時間設定データを出力する
    zone_traveltime_data.to_csv(
        directory_and_file_path["output_zone_traveltime_path"],
        index=False,
        line_terminator="",
        encoding="shift_jis",
    )


def output_csv_land_rate(user_input_data, directory_and_file_path):
    """
    地価変更割合データをcsvで出力する。
    ユーザ入力がない場合は現況地価変更割合データのみを、ユーザ入力がある場合はシナリオ地価変更割合データと現況地価変更割合データをcsvで出力する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    ファイル入力:
        ゾーンデータ(メモリ上)
    ファイル出力:
        (常に出力)Land_Price_Change_Rate.csv
        (ユーザ入力があった場合出力)Land_Price_Change_Rate_[地下変更情報の開始年次].csv
    """
    land_price_change_rate_fields = [
        "zone_code",
        "ChangeRateResidence",
        "ChangeRateCommercial",
    ]
    # 地価変更割合をcsvで出力するためにgeodatabaseからデータを抽出する
    numpy_land_rate_data = [
        list(row)
        for row in arcpy.da.FeatureClassToNumPyArray(
            ZONE_DATA_TMP, ["OBJECTID", land_price_change_rate_fields]
        )
    ]

    # OBJECTIDでソートする
    numpy_land_rate_data = sorted(numpy_land_rate_data, key=lambda x: x[0])

    # OBJECTIDは出力しないため削除する
    numpy_land_rate_data = np.delete(numpy_land_rate_data, slice(0, 1), axis=1)
    # ユーザ入力がない場合は現況データを出力し、ユーザ入力がある場合は現況データとシナリオデータを出力する
    if user_input_data.at["user_data", "land_start_year"] == -1:
        # 現況データ出力
        with open(
            directory_and_file_path["land_price_change_rate_path"],
            "w",
            encoding="shift_jis",
            newline="",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(land_price_change_rate_fields)
            writer.writerows(numpy_land_rate_data)
    else:
        # シナリオデータ出力
        with open(
            directory_and_file_path["output_land_rate_path"],
            "w",
            encoding="shift_jis",
            newline="",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(land_price_change_rate_fields)
            writer.writerows(numpy_land_rate_data)

        # 現況データ作成
        numpy_land_rate_data[:, [1, 2]] = 0
        # 現況データ出力
        with open(
            directory_and_file_path["land_price_change_rate_path"],
            "w",
            encoding="shift_jis",
            newline="",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(land_price_change_rate_fields)
            writer.writerows(numpy_land_rate_data)


def output_csv_migration_rate(user_input_data, directory_and_file_path):
    """
    転入転出割合データをcsvで出力する。
    ユーザ入力がない場合は現況転入転出割合データのみを、
    ユーザ入力がある場合はシナリオ転入転出割合データと現況転入転出割合データをcsvで出力する
    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    ファイル入力:
        ゾーンデータ(メモリ上)
    ファイル出力:
        (常に出力)Migration_Rate.csv
        (ユーザ入力があった場合出力)Migration_Rate_[転入転出割合の開始年次].csv
    """
    migration_rate_fields = ["Migration_Rate_In", "Migration_Rate_Out"]
    migration_rate_base_data = [[0] * len(migration_rate_fields)] * 1

    # ユーザ入力がない場合は現況データを出力し、ユーザ入力がある場合は現況データとシナリオデータを出力する
    if user_input_data.at["user_data", "migration_start_year"] == -1:
        # 現況データ出力
        with open(
            directory_and_file_path["migration_rate_path"],
            "w",
            encoding="shift_jis",
            newline="",
        ) as f:
            writer = csv.writer(f)
            writer.writerow(migration_rate_fields)
            writer.writerows(migration_rate_base_data)
        return

    # シナリオデータ出力
    with open(
        directory_and_file_path["output_migration_rate_path"],
        "w",
        encoding="shift_jis",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(migration_rate_fields)
        # 地価変更割合をcsvで出力
        writer.writerows(
            [
                [
                    user_input_data.at["user_data", "Migration_Rate_In"],
                    user_input_data.at["user_data", "Migration_Rate_Out"],
                ]
            ]
        )

    # 現況データ作成
    migration_rate_base_data = [[0] * len(migration_rate_fields)] * 1
    # 現況データ出力
    with open(
        directory_and_file_path["migration_rate_path"],
        "w",
        encoding="shift_jis",
        newline="",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(migration_rate_fields)
        writer.writerows(migration_rate_base_data)


def output_control_simyear(directory_and_file_path, control_simyear_data):
    """
    control_simyearをcsvで出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        control_simyear_data[list型]:control_simyearデータ
    返値:
        なし

    ファイル出力:
        Control_SimYear.csv
    """
    # Control_SimYear.csv出力
    with open(
        directory_and_file_path["control_simyear_data_path"],
        "w",
        encoding="shift_jis",
        newline="",
    ) as f:
        f.write("\n".join(map(str, control_simyear_data)))


def output_control_siminput(directory_and_file_path, control_siminput_data):
    """
    control_siminputをtxtで出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        control_siminput_data[データフレーム型]:control_siminputデータ
    返値:
        なし

    ファイル出力:
        Control_SimInput.csv
    """
    # Control_SimInput.csv出力
    control_siminput_data.to_csv(
        directory_and_file_path["control_siminput_data_path"],
        encoding="shift_jis",
        header=True,
        index=False,
        line_terminator="",
    )


def output_control_sim(directory_and_file_path):
    """
    control_simデータを作成し、txtで出力する
    引数:
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
    返値:
        なし

    ファイル出力:
        Control_Sim.txt
    """
    # control_simのデータを作成する
    control_sim_data = [
        directory_and_file_path["basedata_path"],
        directory_and_file_path["output_directory_path"],
        directory_and_file_path["sim_output_path"],
    ]

    # Control_Sim.txt出力
    with open(
        directory_and_file_path["control_sim_data_path"],
        "w",
        encoding="shift_jis",
        newline="",
    ) as f:
        f.writelines([d + "\n" for d in control_sim_data])

    # Simulation 直下の Control_Sim.txt を置換
    shutil.copy(
        directory_and_file_path["control_sim_data_path"],
        directory_and_file_path["control_sim_txt_path"],
    )


def output_result(
    user_input_data: pd.DataFrame,
    directory_and_file_path,
    zone_traveltime_data,
    zone_facility_num_data,
    control_simyear_data,
    control_siminput_data: pd.DataFrame,
):
    """
    ユーザ入力が反映されたデータをファイル出力する。
    現況地価変更割合データ、現況転入転出データ、Control_Simデータ、
    Control_SimInputデータ、Control_SimYearデータは常に出力する。
    シナリオゾーンデータ、シナリオゾーン間所用時間設定データ、
    シナリオ施設数データ、シナリオ地価変更割合データ、シナリオ転入転出データはユーザ入力があった場合出力する。

    引数:
        user_input_data[データフレーム型]:ユーザ入力パラメータを纏めたデータフレーム
        directory_and_file_path[Series型]:ファイルやフォルダの絶対パス
        zone_traveltime_data[データフレーム型]:ゾーン間所要時間データ
        zone_facility_num_data[データフレーム型]:施設数データ
        control_simyear_data[list型]:control_simyearデータ
        control_siminput_data[データフレーム型]:control_siminputデータ

    返値:
        なし

    """

    logger = set_log_format("output_result")
    logger.info("Start processing.")

    # 出力ファイルがない場合作成する
    check_and_make_directory(directory_and_file_path)

    # ゾーンデータをcsvで出力 変更がない場合出力しない
    if user_input_data.at["user_data", "city_start_year"] != -1:
        output_csv_zone(directory_and_file_path)

    # 施設数データをcsvで出力 変更がない場合出力しない
    if user_input_data.at["user_data", "facility_start_year"] != -1:
        # シナリオデータ出力
        output_csv_facility_num(
            directory_and_file_path, zone_facility_num_data
        )

    # ゾーン間所用時間設定データをcsv出力
    if user_input_data.at["user_data", "traffic_start_year"] != -1:
        # シナリオデータ出力
        output_csv_zone_traveltime(
            directory_and_file_path, zone_traveltime_data
        )

    # 地価変更割合を出力する
    output_csv_land_rate(user_input_data, directory_and_file_path)

    # 転入転出割合をcsvで出力するためにgeodatabaseからデータを抽出する
    output_csv_migration_rate(user_input_data, directory_and_file_path)

    # Control_SimYear.csv出力
    output_control_simyear(directory_and_file_path, control_simyear_data)

    # Control_SimInput.csv出力
    output_control_siminput(directory_and_file_path, control_siminput_data)

    # control_Sim.txt出力
    output_control_sim(directory_and_file_path)

    logger.info("Complete processing.")


def set_log_format(name):
    log_file_path = str(
        ROOT_DIR_PATH.joinpath(
            "Simulation", "Tool", "Logs", "scenario_setting.log"
        )
    )
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


def main():
    """
    ジオプロセシングツールで入力されたユーザ入力パラメータを受け取り、入力値チェック、現況データの参照を行う。
    ユーザ入力パラメータが反映されたゾーンデータ、施設数データ、
    ゾーン間所用時間設定データ、地価変更割合データ、転入転出データのcsvファイルと
    Control_Sim、Control_SimInput、Contorl_SimYearのtxtファイルを出力する
    ファイル出力後作成した中間ファイルを削除する。

    引数:
        なし
    返値:
        なし

    """

    logger = set_log_format("scenario_setting")
    logger.info("Start processing.")

    # ユーザ入力パラメータの取得
    user_input_data = get_user_parameter()

    # 入力データ取得
    (
        directory_and_file_path,
        zone_traveltime_data,
        zone_facility_num_data,
        control_siminput_data,
        control_simyear_data,
    ) = input_preprocessing(user_input_data)

    # ゾーン情報の更新(施設数、都市情報、地価変更割合、転入転出データの更新)
    zone_facility_num_data = update_zone_setting_info(
        user_input_data, zone_facility_num_data
    )

    # ゾーン間所用時間設定の更新(公共交通情報の更新)
    zone_traveltime_data = update_zone_traveltime(
        user_input_data, zone_traveltime_data
    )

    # Control_SimYearの更新
    control_simyear_data = update_control_simyear(
        user_input_data, control_simyear_data
    )

    # Control_SimInputの更新
    control_siminput_data = update_control_siminput(
        user_input_data, directory_and_file_path, control_siminput_data
    )

    # ファイル出力
    output_result(
        user_input_data,
        directory_and_file_path,
        zone_traveltime_data,
        zone_facility_num_data,
        control_simyear_data,
        control_siminput_data,
    )

    logger.info("Complete processing.")

    # [中間ファイルの削除]
    # メモリの解放
    arcpy.management.Delete(ZONE_DATA_TMP)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # tracebackは出力されません
        arcpy.AddError(e)
