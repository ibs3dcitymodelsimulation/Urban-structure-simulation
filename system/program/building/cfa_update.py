# -*- coding: utf-8 -*-

import os
import sys

import pandas as pd


def cfa_update(df, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    df_agg = df.groupby(["zone"], as_index = False).agg({f"area_residence{year}":"sum", f"area_commercial{year}":"sum"})
    df_agg = df_agg.rename(columns = {"zone":"zone_code", f"area_residence{year}":"farea_residence", f"area_commercial{year}":"farea_shop"})
    
    """ # 0埋めしておく """
    df_agg = df_agg.fillna(0)
    
    if(outset["設定値"] == "T"):
        df_agg.to_csv(rf"{outset['フォルダ名']}/建物面積集計_{year}.csv", index = False, encoding = "cp932")

    return df_agg
