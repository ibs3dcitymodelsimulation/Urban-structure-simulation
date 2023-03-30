# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def house_landprice_model(df_zone_org, df_pop, df_area, df_flarea, df_prm, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # ゾーンデータのコピー """
    df_zone = df_zone_org.copy()
    
    """ # 人口密度の計算 """
    """ # 人口と面積をマージする """
    df_zone = pd.merge(df_zone, df_pop, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, df_area, how = "left", on = ["zone_code"])
    
    """ # ゾーン別人口は、全て埋まるとは限らないので、「0」埋めしておく """
    df_zone["pop_all"] = df_zone["pop_all"].fillna(0)
    df_zone["AREA"] = df_zone["AREA"].fillna(0)
    
    """ # 人口密度をha単位で計算 """
    df_zone["popdens_ha"] = df_zone["pop_all"] / (df_zone["AREA"] / 10000)
    
    """ # 住宅延べ床面積をマージする """
    df_zone = pd.merge(df_zone, df_flarea[["zone_code", "farea_residence"]], how = "left", on = ["zone_code"])

    """ # ゾーン別住宅延べ床面積を「0」埋めしておく """
    df_zone["farea_residence"] = df_zone["farea_residence"].fillna(0)
    
    """ # 住宅地価の計算1 : ln版 """
    df_zone["ln(住宅地価)"] = 0.0
    for col in df_prm.index:
        if(col == "const"):
            df_zone["ln(住宅地価)"] += df_prm.loc[col, "param"]
        else:
            df_zone["ln(住宅地価)"] += df_prm.loc[col, "param"] * df_zone[col]
    
    """ # 住宅地価の計算2 : exp """
    df_zone["住宅地価"] = np.exp(df_zone["ln(住宅地価)"])

    """ # この時点で一回出力 """
    if(outset["設定値"] == "T"):
        df_zone.to_csv(rf"{outset['フォルダ名']}/住宅地価_{year}.csv", index = False, encoding = "cp932")
    
    """ # 住宅地価として残して置けばいいものだけ返す """
    df_hlp = df_zone[["zone_code", "住宅地価"]].copy()
    
    return df_hlp
