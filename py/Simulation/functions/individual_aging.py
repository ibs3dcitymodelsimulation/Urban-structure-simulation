# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 15:42:22 2023

@author: ktakahashi
"""

import sys

import numpy as np
import pandas as pd



def agerank_check(age):
    if(85 <= age):
        return 18
    else:
        return age // 5 + 1
    
def add_age(age, add, category):
    """ # カテゴリが「99(=死亡)の場合、年は取らない """
    if(category == 99):
        return age
    
    """ # それ以外の場合 """
    age += add
    return age
    

def aging(df_individual, year, agerank_max):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の年を作っておく """
    period = 1
    year1pb = year - period
    
    """ # 1期前の年齢に期間分の年数を加算する """
    df_individual[f"Age{year}"] = pd.Series(np.vectorize(add_age)
                                               (df_individual[f"Age{year1pb}"],
                                                period,
                                                df_individual[f"Marital_Status_Family_Position{year}"]))
        
    """ # 年齢階層を変化させる """
    df_individual[f"Age_Group{year}"] = pd.Series(np.vectorize(agerank_check)(df_individual[f"Age{year}"]))
        
    """ # 加齢終了 """
    return df_individual