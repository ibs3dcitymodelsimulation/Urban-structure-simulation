# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 13:43:19 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely.geometry import Point

def calc_zonearea(df_zone, df_poly_org, crs_code):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # ポリゴンのデータフレームをコピーして使う """
    df_poly = df_poly_org.copy()
        
    """ # 座標系を変換する """
    df_poly = df_poly.to_crs(crs_code)
    
    """ # 面積を求める """
    df_poly["AREA"] = df_poly["geometry"].area
    # print(df_poly)
    
    """ # ゾーンコード一覧に面積を対応付けて """
    df_zone = pd.merge(df_zone, df_poly[["zone_code", "AREA"]], how = "left", on = ["zone_code"])
    # print(df_zone)
    
    """ # 戻す """
    return df_zone
