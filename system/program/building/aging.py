# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd

def add_age(age, bflag, exist, step):
    if(exist == 2):
        return -2
    
    if(bflag == 1):
        return 1
    else:
        age += step
        return age

def aging(df, year, period, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の西暦 """
    year1pb = year - period

    """ # 年齢の追加 """
    df[f"building_age{year}"] = pd.Series(np.vectorize(add_age)(df[f"building_age{year1pb}"], df[f"建設有無フラグ{year}"], df[f"existing{year}"], period))
    df[f"building_age{year}"] = df[f"building_age{year}"].replace(-2, np.nan)

    """ # 出力 """
    if(outset["設定値"] == "T"):
        df.to_csv(rf"{outset['フォルダ名']}/建物データ_{year}.csv", index = False, encoding = "cp932")
    
    """ # 返す """
    return df

