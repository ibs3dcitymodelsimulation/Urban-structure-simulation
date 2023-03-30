# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def calc_height1f(exists, bflag, usage, prm):
    """ # 辞書でパラメータのデータフレームを受けておく """
    df_prm = prm["prm"]
    
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return -9.9 # あり得ない値を返却しておく
    
    """ # 建設が無かった場合、高さ更新はないので """
    if(bflag == 0):
        return -9.9
    
    """ # 建物が存在 & 新規建設の場合 """
    height = df_prm.loc[usage]
    
    return height

def calc_height2f(exists, bflag, usage, storey, prm):
    """ # 辞書でパラメータのデータフレームを受けておく """
    df_prm = prm["prm"]

    """ # 建物が存在しない場合 """
    if(exists == 2):
        return -9.9 # あり得ない値を返却しておく
    
    """ # 建設が無かった場合、高さ更新はないので """
    if(bflag == 0):
        return -9.9

    """ # 建物が存在 & 新規建設の場合 """
    param = df_prm.loc[usage]
    height = param * (storey - 1)
    
    return height

def calc_building_height(exists, bflag, height, height1f, height2fo, usage):
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return -1.0

    """ # 建設が無かった場合、高さ更新はないので """
    if(bflag == 0):
        return height
    
    """ # 建物が存在 & 新規建設の場合 """
    if(usage == "空地"):
        height = -1
    else:
        height = height1f + height2fo
    return height


def building_height_model(df_build, prm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作る """
    year1pb = year - period
    
    """ # まずは1F部分の高さ """
    dic_prm = {"prm" : prm["param_1F"]}
    df_build["height_1F"] = pd.Series(np.vectorize(calc_height1f)(df_build[f"existing{year}"], df_build[f"建設有無フラグ{year}"],
                                                                  df_build[f"yoto{year}"], dic_prm))
    
    """ # 2F以降の高さ """
    dic_prm = {"prm" : prm["param_2F"]}
    df_build["height_2Fo"] = pd.Series(np.vectorize(calc_height2f)(df_build[f"existing{year}"], df_build[f"建設有無フラグ{year}"],
                                                                  df_build[f"yoto{year}"], df_build[f"storey{year}"], dic_prm))
    
    """ # 建物高さの計算 """
    df_build[f"display_high_median{year}"] = pd.Series(np.vectorize(calc_building_height)
                                                       (df_build[f"existing{year}"], df_build[f"建設有無フラグ{year}"], 
                                                        df_build[f"display_high_median{year1pb}"],
                                                        df_build["height_1F"], df_build["height_2Fo"], df_build[f"yoto{year}"]))
    
    
    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/建物高さモデル_{year}.csv", index = False, encoding = "cp932")
        
    """ # 追加列を削除 """
    df_build = df_build.drop(["height_1F", "height_2Fo"], axis = 1)
    
    """ # 返す """
    return df_build
