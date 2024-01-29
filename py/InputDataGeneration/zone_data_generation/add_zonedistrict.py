# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 21:16:51 2023

@author: ktakahashi
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point
from collections import Counter


def add_zonedistrict(df_zone, df_poly_org, df_district_org, crs_code):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # ポリゴンのデータフレームをコピーして使う """
    df_poly = df_poly_org.copy()
    df_dtct = df_district_org.copy()
    
    """ # 座標系を変換する """
    df_poly = df_poly.to_crs(crs_code)
    df_dtct = df_dtct.to_crs(crs_code)
    
    """ # 用途情報ポリゴンの面積を求めておく """
    df_dtct["area"] = df_dtct["geometry"].area
    # print(df_dtct)

    """ # 整数型にしておく """
    df_dtct["yotochiki"] = df_dtct["yotochiki"].astype("int")
    df_dtct["kenpei"] = df_dtct["kenpei"].astype("int")
    df_dtct["yoseki"] = df_dtct["yoseki"].astype("int")


    """ # ゾーンポリゴンと用途地域をgeometryでマージする """
    gdf = gpd.sjoin(df_poly, df_dtct, how = "left", predicate = "intersects")
    # print(gdf.isnull().sum())
    # print(gdf.dtypes)

    """ # ゾーンごとに代表用途を選択 """
    def choose_representative_use(group):
        use_counts = Counter(group["yotochiki"])
        sorted_count = group.sort_values(by = "area", ascending = False)
        
        if(len(use_counts) > 1):
            # most_common_use = sorted_count.iloc[0]["yotochiki"]
            # target_row = sorted_count.iloc[0]
            most_common_use = max(use_counts, key=use_counts.get)
            target_rows = sorted_count[sorted_count["yotochiki"] == most_common_use]
            if len(target_rows) > 1:
                # 用途の数が同じ場合、面積が最大のものを選択
                target_row = target_rows.sort_values(by="area", ascending=False).iloc[0]
            else:
                target_row = target_rows.iloc[0]
        else:
            most_common_use = use_counts.most_common(1)[0][0]
            target_row = group.iloc[0]
        
        # target_row = sorted_count.iloc[0]
        usage = target_row["yotochiki"]
        buildingCoverageRate = target_row["kenpei"]
        floorAreaRate = target_row["yoseki"]
        
        if(np.isnan(usage)):
            usage = 99.0
        if(np.isnan(buildingCoverageRate)):
            buildingCoverageRate = 60.0
        if(np.isnan(floorAreaRate)):
            floorAreaRate = 100.0
                    
        # print("group : \n", group)
        # print("use_counts : \n", use_counts)
        # print("sorted : \n", sorted_count)
        # print("most_common : \n", most_common_use)
        # print("get : \n", usage, buildingCoverageRate, floorAreaRate)
        # print("type : \n", type(usage), type(buildingCoverageRate), type(floorAreaRate))
        
        return usage, floorAreaRate, buildingCoverageRate
            
    
    gdf_rep = gdf.groupby("zone_code").apply(choose_representative_use)
    gdf_rep = gdf_rep.reset_index()
    
    """ # 用途,容積率,建蔽率がタプルで返ってくるので分割 """
    gdf_rep[["UseDistrict", "floorAreaRate", "buildingCoverageRate"]] = pd.DataFrame(gdf_rep[0].tolist(), index = gdf_rep.index)
    
    """ # 要らない列を落としておく """
    gdf_rep = gdf_rep.drop(columns = [0])
    
    # print(gdf_rep)
    
    """ # ゾーンデータにマージする """
    # print(df_zone.dtypes)
    # print(gdf_rep.dtypes)
    df_zone = pd.merge(df_zone, gdf_rep, how = "left", on = ["zone_code"])
    # print(df_zone)
    
    """ # 戻す """
    return df_zone
