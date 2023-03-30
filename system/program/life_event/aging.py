# -*- coding: utf-8 -*-

import sys

import numpy as np
import pandas as pd



def agerank_check(age):
    if(85 <= age):
        return 18
    else:
        return age // 5 + 1
    
def add_age(age, add, category):
    """ # カテゴリが「99(=死亡)」の場合、年は取らない """
    if(category == 99):
        return age
    
    """ # それ以外の場合 """
    age += add
    return age
    

def aging(df_individual, year, period, agerank_max):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の年を作っておく """
    year1pb = year - period
    
    """ # 1期前の年齢に期間分の年数を加算する """
    df_individual[f"世帯票_年齢{year}"] = pd.Series(np.vectorize(add_age)
                                               (df_individual[f"世帯票_年齢{year1pb}"],
                                                period,
                                                df_individual[f"カテゴリ{year}"]))
    
    """ # 最小子供年齢の加算 """
    df_individual[f"世帯内最小年齢{year}"] = pd.Series(np.vectorize(add_age)
                                               (df_individual[f"世帯内最小年齢{year1pb}"],
                                                period,
                                                df_individual[f"カテゴリ{year}"]))
    
    """ # 年齢階層を変化させる """
    df_individual[f"年齢階層{year}"] = pd.Series(np.vectorize(agerank_check)(df_individual[f"世帯票_年齢{year}"]))
        
    """ # 加齢終了 """
    return df_individual