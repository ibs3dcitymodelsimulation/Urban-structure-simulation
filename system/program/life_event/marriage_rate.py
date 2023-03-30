# -*- coding: utf-8 -*-

import sys
import pandas as pd

def marriage_rate(df_individual, year, outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 生存者を抽出 """
    df_lives = df_individual[df_individual[f"カテゴリ{year}"] != 99].reset_index(drop = True)
    df_lives["人口"] = 1
    
    """ # 年齢別配偶関係別人口集計 """
    marrige_pop = df_lives.groupby([f"世帯票_年齢{year}", f"配偶関係{year}"], as_index = False).agg({"人口":sum})
    
    """ # 年齢別人口集計 """
    age_pop = df_lives.groupby([f"世帯票_年齢{year}"], as_index = False).agg({"人口":sum})
    age_pop = age_pop.rename(columns = {"人口":"人口計"})
    
    """ # 2つをmerge """
    marrige_pop = pd.merge(marrige_pop, age_pop, on = [f"世帯票_年齢{year}"])
    
    """ # 配偶関係が 2 (=有配偶)である個人を抽出 """
    marrige_pop = marrige_pop[marrige_pop[f"配偶関係{year}"] == 2].reset_index(drop = True)
    marrige_pop = marrige_pop.rename(columns = {"人口":"有配偶人口"})
    
    """ # 有配偶率 """
    marrige_pop["有配偶率"] = marrige_pop["有配偶人口"] / marrige_pop["人口計"]

    """ # 出力 """
    if(outset["設定値"] == "T"):
        df_individual.to_csv(rf"{outset['フォルダ名']}/有配偶率_{year}.csv", index = False, encoding = "cp932")
    
    return marrige_pop
    
    