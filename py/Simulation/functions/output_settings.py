# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 11:37:36 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd



def output(df_individual, df_build, df_zone, year, root_out):
    """ # 出力調整 """
    
    """ # 個人データに必要なもの """
    col_list = ["Personal_UniqueId", f"zone_code{year}", "Gender", f"Age{year}", "Expansion_Factor",
                f"Marital_Status{year}", f"Family_Position{year}", f"Marital_Status_Family_Position{year}",
                f"Age_Group{year}"]
    
    df_individual = df_individual[col_list].copy()

    """ # 建物データからゾーン別商業地価の平均を計算する """
    df_clp = df_build.groupby(["zone_code"], as_index = False).agg({"Landprice_Commercial":"mean"})
    df_clp = df_clp.rename(columns = {"Landprice_Commercial":"LandPrice_commercial"})
    
    """ # 建物データに必要なもの """
    col_list = ["buildingID", f"Usage{year}", "YearOfConstruction", f"Height{year}", f"storeysAboveGround{year}",
                f"totalFloorArea{year}", "FootprintArea", f"Existing{year}", "RoadWidth", "zone_code",
                f"BuildingAge{year}", "Integrated_buildingID", "SimTargetFlag", "Lat", "Lon"]
    df_build = df_build[col_list].copy()
    
    """ # ここで, 不能扱いをNaNに戻さないと """
    df_build[f"Usage{year}"] = df_build[f"Usage{year}"].replace(-2, np.nan)
    df_build[f"Height{year}"] = df_build[f"Height{year}"].replace(-1, np.nan)
    df_build[f"storeysAboveGround{year}"] = df_build[f"storeysAboveGround{year}"].replace(-2, np.nan)
    df_build[f"totalFloorArea{year}"] = df_build[f"totalFloorArea{year}"].replace(-1, np.nan)
    df_build[f"BuildingAge{year}"] = df_build[f"BuildingAge{year}"].replace(-1, np.nan)
    
    """ # 末尾の{year}を外す """
    df_build_out = df_build.copy().rename(columns = {f"Usage{year}" : "Usage", 
                                            f"Height{year}" : "Height",
                                            f"storeysAboveGround{year}" : "storeysAboveGround",
                                            f"totalFloorArea{year}" : "totalFloorArea",
                                            f"Existing{year}" : "Existing",
                                            f"BuildingAge{year}" : "BuildingAge" })

    """ # ゾーンデータに必要なもの """
    col_list = ["zone_code", "AREA", "Avg_Dist_sta_centre", "Avg_Dist_sta_main", "Avg_Dist_sta_other",
                "UseDistrict", "floorAreaRate", "buildingCoverageRate",
                f"landprice_house{year}"]
    df_zone = df_zone[col_list]
    
    """ # ゾーンデータに商業地価をくっつける """
    df_zone = df_zone.rename(columns = {f"landprice_house{year}":"LandPrice_residence"})
    df_zone = pd.merge(df_zone, df_clp, how = "left", on = ["zone_code"])
    df_zone["LandPrice_commercial"] = df_zone["LandPrice_commercial"].fillna(0)
    
    """ # 出力 """    
    df_individual.to_csv(rf"{root_out}/Individual{year}.csv", index = False, encoding = "cp932")
    df_build_out.to_csv(rf"{root_out}/Building{year}.csv", index = False, encoding = "cp932")
    df_zone.to_csv(rf"{root_out}/zone{year}.csv", index = False, encoding = "cp932")
    
    """ # 出力しおわったので、再度、nanを数値に戻す """
    df_build[f"Usage{year}"] = df_build[f"Usage{year}"].fillna(-2)
    df_build[f"Height{year}"] = df_build[f"Height{year}"].fillna(-1)
    df_build[f"storeysAboveGround{year}"] = df_build[f"storeysAboveGround{year}"].fillna(-2)
    df_build[f"totalFloorArea{year}"] = df_build[f"totalFloorArea{year}"].fillna(-1)
    df_build[f"BuildingAge{year}"] = df_build[f"BuildingAge{year}"].fillna(-1)
    
    """ # 出力し終わったので,地価を落とす """
    df_zone = df_zone.drop(["LandPrice_residence", "LandPrice_commercial"], axis = 1)
    # print(df_zone.columns)
    # sys.exit(0)

    return df_individual, df_build, df_zone
    