# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def zone_pop_update(df_individual, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # カテゴリ「99(=死亡)」を除いて拡大係数をゾーン別に集計 """
    df_agg = df_individual[df_individual[f"カテゴリ{year}"] != 99].groupby([f"現住所{year}"], as_index = False).agg({"拡大係数":"sum"})
    df_agg = df_agg.rename(columns = {f"現住所{year}":"zone_code", "拡大係数":"pop_all"})

    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_agg.to_csv(rf"{outset['フォルダ名']}/年次別ゾーン別人口_{year}.csv", index = False, encoding = "cp932")
        
    """ # ゾーン別人口更新 """
    return df_agg



