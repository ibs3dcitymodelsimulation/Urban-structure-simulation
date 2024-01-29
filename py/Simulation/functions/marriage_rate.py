# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 15:48:28 2023

@author: ktakahashi
"""

import sys
import pandas as pd

def marriage_rate(df_individual, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 生存者を抽出 """
    df_lives = df_individual[df_individual[f"Marital_Status_Family_Position{year}"] != 99].reset_index(drop = True)
    
    """ # 年齢別配偶関係別人口集計 """
    marrige_pop = df_lives.groupby([f"Age{year}", f"Marital_Status{year}"], as_index = False).agg({"Expansion_Factor":"sum"})
    marrige_pop = marrige_pop.rename(columns = {"Expansion_Factor":"人口"})
    
    """ # 年齢別人口集計 """
    age_pop = df_lives.groupby([f"Age{year}"], as_index = False).agg({"Expansion_Factor":"sum"})
    age_pop = age_pop.rename(columns = {"Expansion_Factor":"人口計"})
    
    """ # 2つをmerge """
    marrige_pop = pd.merge(marrige_pop, age_pop, on = [f"Age{year}"])
    
    """ # 配偶関係が 2 (=有配偶)である個人を抽出 """
    marrige_pop = marrige_pop[marrige_pop[f"Marital_Status{year}"] == 2].reset_index(drop = True)
    # print(marriage_rate)
    # sys.exit(0)
    marrige_pop = marrige_pop.rename(columns = {"人口":"有配偶人口"})
    
    """ # 有配偶率 """
    marrige_pop["有配偶率"] = marrige_pop["有配偶人口"] / marrige_pop["人口計"]

    """ # 出力 """
    # df_individual.to_csv(rf"{root_out}/有配偶率_{year}.csv", index = False, encoding = "cp932")

    return marrige_pop
