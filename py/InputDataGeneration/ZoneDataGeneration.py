# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 14:53:29 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import distance_matrix

import submodule.read_initial as sri
import zone_data_generation.calc_zonearea as cza
import zone_data_generation.calc_stationdist as csd
import zone_data_generation.add_zonedistrict as azd
import zone_data_generation.add_facilitynumber as afn


def main():
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # Control Inputの読み込み """
    with open(rf"Control_Input.txt", mode = "r") as ci:
        root_inp = next(ci).strip()
        root_out = next(ci).strip()
        crs_code = next(ci).strip()
    
    """ # 出力先 """
    if not(os.path.exists(root_out)):
        os.makedirs(root_out)

    """ # input file path dataframe の作成 """
    dic_control = {
        "key":["ゾーンポリゴン", "都市計画情報", "鉄道駅", "施設情報"],
        "path":["Zone_Polygon.shp", "Urban_Planning_Info.shp", "Rail_Station.csv", "Facility_Point.csv"]}
    df_control = pd.DataFrame(dic_control)
    # print(df_control)
    
    # """ # setting : crs_code """
    # crs_code = 6678

    # """ # controlファイルの読み込み """
    # df_control = sri.read_control(r"../zonedata_control.csv")
    # print(df_control)
    
    # """ # settingファイルの読み込み """
    # df_set = sri.read_control(r"../zonedata_setting.csv", index = "key")
    # print(df_set)
    
    """ # インプットファイルを取り込んでおく """
    dfs_dict = {}
    for i in range(len(df_control)):
        fkey = df_control.loc[i, "key"]
        dfs_dict[fkey] = sri.read_input(root_inp, df_control.loc[i, "path"])
    # print(dfs_dict)

    # ----- ! Zone.csv 作成 ! ----- #    
    """ # ゾーンデータを格納するデータフレームを作成 """
    df_zone = dfs_dict["ゾーンポリゴン"]["zone_code"].copy()
    
    """ # 面積の追加 """
    df_zone = cza.calc_zonearea(df_zone, dfs_dict["ゾーンポリゴン"], crs_code)
    
    """ # 各ゾーンから駅への距離を追加 """
    df_zone = csd.calc_statdist(df_zone, dfs_dict["ゾーンポリゴン"], dfs_dict["鉄道駅"], 
                                crs_code)
    
    """ # 各ゾーンの代表用途地域の付与 """
    df_zone = azd.add_zonedistrict(df_zone, dfs_dict["ゾーンポリゴン"], 
                                    dfs_dict["都市計画情報"], crs_code)
    # print(df_zone)
    
    """ # 出力 """
    df_zone.to_csv(rf"{root_out}/Zone.csv", index = False, encoding = "cp932")
    # ----- ! Zone.csv 作成 ! ----- #    

    # ----- ! ZoneFacilityNum.csv 作成 ! ----- #    
    """ # ゾーンデータを格納するデータフレームを作成 """
    df_zone = dfs_dict["ゾーンポリゴン"]["zone_code"].copy()

    """ # ゾーン別施設数の追加 """
    df_zone = afn.agg_facility(df_zone, dfs_dict["ゾーンポリゴン"], dfs_dict["施設情報"])

    """ # 出力 """
    df_zone.to_csv(rf"{root_out}/Zone_FacilityNum.csv", index = False, encoding = "cp932")
    # ----- ! ZoneFacilityNum.csv 作成 ! ----- #    

    # ----- ! Zone_Centroid_Distance_Table.csv 作成 ! ----- #    
    """ # ゾーンポリゴンのepsgを変換 """
    zonepoly = dfs_dict["ゾーンポリゴン"].copy()
    zonepoly = zonepoly.to_crs(epsg=crs_code)

    """ # 重心を計算 """
    zonepoly['centroid'] = zonepoly['geometry'].centroid

    """ # 重心の座標をNumPy配列に変換 """
    centroid_coords = zonepoly['centroid'].apply(lambda p: (p.x, p.y)).to_list()

    """ # SciPyのdistance_matrixを用いて距離行列を計算 """
    dist_matrix = distance_matrix(centroid_coords, centroid_coords)

    """ # 距離行列をDataFrameに変換 """
    dist_df = pd.DataFrame(dist_matrix, index=zonepoly['zone_code'], columns=zonepoly['zone_code'])

    """ # 距離が800m未満のレコードに絞る """
    filtered_dist_df = dist_df[(dist_df < 800)]

    """ # 縦もち変換 """
    melted_dist_df = filtered_dist_df.reset_index().melt(id_vars='zone_code', var_name='zone_code_2', value_name='dist').dropna()

    """ # 出力 """
    melted_dist_df.to_csv(rf"{root_out}/Zone_Centroid_Distance_Table.csv", index = False, encoding = "cp932")
    # ----- ! Zone_Centroid_Distance_Table.csv 作成 ! ----- #    

if(__name__ == "__main__"):
    main()