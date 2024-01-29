# -*- coding: utf-8 -*-
"""
Created on Wed Aug  9 19:04:15 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point

def agg_facility(df_zone, df_poly_org, df_facility):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # ポリゴンのデータフレームをコピーして使う """
    df_poly = df_poly_org.copy()
    
    """ # Pointオブジェクトを作成する """
    df_facility["geometry"] = df_facility.apply(lambda row : Point(float(row["lon"]), float(row["lat"])), axis = 1)
    
    """ # GeoDataFrameへ変換する """
    gdf_facility = gpd.GeoDataFrame(df_facility, geometry = "geometry")

    """ # ポリゴンに含まれる場合、対応するzone_codeを取得 """
    def find_zone_code(point):
        mask = df_poly['geometry'].contains(point)
        zone_code = df_poly.loc[mask, 'zone_code'].values
        if len(zone_code) > 0:
            return zone_code[0]
        return None
    
    """ # 新しい列としてzone_codeを追加 """
    gdf_facility["zone_code"] = gdf_facility["geometry"].apply(find_zone_code)
    
    """ # サンプル集計用に列をいれて """
    gdf_facility["sample"] = 1
    
    """ # 列名の辞書を作る """
    # 1:図書館, 2:病院, 3:診療所, 4:小学校, 5:中学校, 6:幼稚園こども園
    dic_name = {1:"fnum_Library", 2:"fnum_Hospital", 3:"fnum_Clinic",
                4:"fnum_ElementarySchool", 5:"fnum_MiddleSchool", 6:"fnum_PreSchool"}
    # print(gdf_facility.dtypes)
    
    """ # ゾーンで集計 """
    gdf_fac_agg = pd.pivot_table(gdf_facility, values = "sample", index = "zone_code", columns = "facility_type", aggfunc = "sum")
    gdf_fac_agg = gdf_fac_agg.reset_index().fillna(0).rename(columns = dic_name)
    
    """ # ゾーンデータにマージする """
    df_zone = pd.merge(df_zone, gdf_fac_agg, how = "left", on = ["zone_code"])
    df_zone = df_zone.fillna(0)
    
    """ # 戻す """
    return df_zone
