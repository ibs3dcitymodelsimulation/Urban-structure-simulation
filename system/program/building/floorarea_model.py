# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def calc_area1f(exists, usage, area, prm):
    """ # 辞書で渡したパラメータをデータフレームで受けておく """
    df_prm = prm["prm"]
    
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return 0.0
    
    """ # 建物がある場合 """
    param = df_prm[usage]
    area = param * area
    
    return area
    
def calc_area2fo(exists, usage, area, storey, prm):
    """ # 辞書で渡したパラメータをデータフレームで受けておく """
    df_prm = prm["prm"]
    
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return 0.0

    """ # 建物がある場合 """
    param = df_prm[usage]
    area = param * area * (storey - 1)
    
    return area

def calc_residence_area(exists, usage, area1f, area2fo):
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return 0.0
    
    """ # 建物がある → 用途によって分類 """
    if(usage in ["住宅", "共同住宅"]):
        area = area1f + area2fo
    elif(usage == "商業施設"):
        area = 0.0
    elif(usage in ["店舗等併用住宅", "店舗等併用共同住宅"]):
        area = area1f
    
    """ # return """
    return area
    
def calc_commercial_area(exists, usage, area1f, area2fo):
    """ # 建物が存在しない場合 """
    if(exists == 2):
        return 0.0

    """ # 建物がある → 用途によって分類 """
    if(usage in ["住宅", "共同住宅"]):
        area = 0.0
    elif(usage == "商業施設"):
        area = area1f + area2fo
    elif(usage in ["店舗等併用住宅", "店舗等併用共同住宅"]):
        area = area2fo
        
    """ # return """
    return area


def floor_area_model(df_build, prm, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦を作る """
    year1pb = year - period
    
    """ # 1F部分面積 """
    dic_prm = {"prm":prm["param_1F"]}
    df_build["area_1F"] = pd.Series(np.vectorize(calc_area1f)(df_build[f"existing{year}"], df_build[f"yoto{year}"], 
                                                              df_build["AREA"], dic_prm))
    
    """ # 2F以降部分面積 """
    dic_prm = {"prm":prm["param_2F"]}
    df_build["area_2Fo"] = pd.Series(np.vectorize(calc_area2fo)(df_build[f"existing{year}"], df_build[f"yoto{year}"], 
                                                                df_build["AREA"], df_build[f"storey{year}"], dic_prm))
    
    """ # 住宅系面積 """
    df_build[f"area_residence{year}"] = pd.Series(np.vectorize(calc_residence_area)
                                                  (df_build[f"existing{year}"], df_build[f"yoto{year}"],
                                                   df_build["area_1F"], df_build["area_2Fo"]))

    """ # 商業系面積 """
    df_build[f"area_commercial{year}"] = pd.Series(np.vectorize(calc_commercial_area)
                                                  (df_build[f"existing{year}"], df_build[f"yoto{year}"],
                                                   df_build["area_1F"], df_build["area_2Fo"]))

    """ # 床面積を追加しておく """
    df_build[f"floorarea{year}"] = df_build[f"area_residence{year}"] + df_build[f"area_commercial{year}"]

    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_build.to_csv(rf"{outset['フォルダ名']}/延べ床面積モデル_{year}.csv", index = False, encoding = "cp932")
        
    """ # 追加した列を削除しておく """
    df_build = df_build.drop(["area_1F", "area_2Fo"], axis = 1)
    
    """ # これで返せばいいはず """
    return df_build

