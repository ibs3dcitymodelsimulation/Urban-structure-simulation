# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def col_replacer(defalut, val, cond_val, cond):
    if(cond_val == cond):
        return val
    else:
        return defalut

def convert_cityGML(df_build_org, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # コピーして使う """
    df_build = df_build_org.copy()
    # print(df_build)
    
    """ # 使用列だけ残す """
    cols = ["tatemono_code", "landuse", "kenpei", "maxfaratio",
            "yotochiki", "shigaika", "kyoju_yudo", "toshikino_yudo",
            "high_toshikino_yudo", "AREA", "display_high_median",
            "yoto", "existing", "building_age", "storey", "floorarea",
            "空家フラグ", "変遷フラグ"]    
    df_build = df_build[cols].copy()

    
    """ # 用途対象外の建物を「その他」とする """
    df_build["yoto"] = df_build["yoto"].apply(lambda x : x if x in ['住宅', '商業施設', '共同住宅', '店舗等併用住宅', '店舗等併用共同住宅', '空地'] else "その他")
    
    """ # 建物が存在しない場合(existing = 2)、用途を「空地」、高さを「０」にする """
    df_build["yoto"] = pd.Series(np.vectorize(col_replacer)(df_build["yoto"], "空地", df_build["existing"], 2))
    df_build["display_high_median"] = pd.Series(np.vectorize(col_replacer)(df_build["display_high_median"], 0, df_build["existing"], 2))
    
    """ # 対象外建物と空地は築年数を「-1」にする """
    df_build["building_age"] = pd.Series(np.vectorize(col_replacer)(df_build["building_age"], -1, df_build["yoto"], "その他"))
    df_build["building_age"] = pd.Series(np.vectorize(col_replacer)(df_build["building_age"], -1, df_build["yoto"], "空地"))
    
    """ # 各種データをコード化する """
    """ # 用途地域を再度コード化 """
    yotochiki_codes = { "第一種低層住居専用地域" : 1,
                        "第二種低層住居専用地域" : 2,
                        "第一種中高層住居専用地域" : 3,
                        "第二種中高層住居専用地域" : 4,
                        "第一種住居地域" : 5,
                        "第二種住居地域" : 6,
                        "準住居地域" : 7,
                        "近隣商業地域" : 8,
                        "商業地域" : 9,
                        "準工業地域" : 10,
                        "工業地域" : 11,
                        "工業専用地域" : 12,
                        "市街化調整区域" : -1}
    df_build["yotochiki"] = df_build["yotochiki"].replace(yotochiki_codes)
    
    """ # 用途をコード化 """
    yoto_codes = {  '住宅' : 1,
                    '共同住宅' : 2,
                    '商業施設' : 3,
                    '店舗等併用住宅' : 4,
                    '店舗等併用共同住宅' : 5,
                    '空地' : 6,
                    'その他' : 7}
    df_build["yoto"] = df_build["yoto"].replace(yoto_codes)
    
    """ # 空家フラグをコード化 """
    empty_code = {0:1, 1:2, "推計対象外":3}
    df_build["empty_home_flg"] = df_build["空家フラグ"].map(empty_code)
    
    """ # 変遷フラグをコード化 """
    trans_code = {'建物 → 建物（維持）' : 1,
                  '建物 → 建物（建て替え）' : 2,
                  '空地 → 建物（建て替え）' : 3,
                  '建物 → 空地' : 4,
                  '空地 → 空地' : 5,
                  '推計対象外' : 6}
    df_build["transition_flg"] = df_build["変遷フラグ"].map(trans_code)
    
    """ # 日本語列名を落とす """
    df_build = df_build.drop(["空家フラグ", "変遷フラグ"], axis = 1)
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/building_data_for_cityGML_{year}.csv", index = False, encoding = "cp932")

