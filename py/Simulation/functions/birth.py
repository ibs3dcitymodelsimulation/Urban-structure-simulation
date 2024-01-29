# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 15:56:08 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd

def birth_flag(category, birth_rate, rnum):
    """ # 出生判定 """
    if(str(category)[:1] == "2" and birth_rate > rnum):
        """ # 婚姻状態で、出生率が乱数を上回れば出生と判定する """
        return 1
    else:
        return 0

def add_properties(df_individual, nchild, year, birth_year, year1pb):
    
    """ # 個人IDの最大値 """
    maxID = df_individual["Personal_UniqueId"].max()

    """ # 出生者のデータフレーム """
    df_children = pd.DataFrame(index = list(range(maxID, maxID + nchild)))
    
    """ # ID """
    df_children["Personal_UniqueId"] = list(range(maxID, maxID + nchild))
    # df_children["Personal_UniqueId"] = df_children["個人ID"].astype(str).str.pad(7, fillchar = "0").astype(int)
    
    """ # 性別 """
    df_children["Gender"] = list(np.random.randint(1, 3, nchild))
    
    """ # 年齢 """
    df_children[f"Age{year}"] = year - birth_year
    
    """ # 年齢階層 """
    df_children[f"Age_Group{year}"] = 1
    
    """ # 配偶関係 """
    df_children[f"Marital_Status{year}"] = 1
    
    """ # カテゴリ """
    df_children[f"Marital_Status_Family_Position{year}"] = 17
    
    """ # 世帯内地位 """
    df_children[f"Family_Position{year}"] = 7
    
    # """ # 最小子供年齢 (= ここで生まれた人の年齢) """
    # df_children[f"世帯内最小年齢{year}"] = df_children[f"世帯票_年齢{year}"].copy()
    
    """ # 住所コード """
    df_children[f"zone_code{year1pb}"] = df_individual[df_individual[f"出生有フラグ{birth_year}"] == 1][f"zone_code{year1pb}"].tolist()

    """ # 拡大係数 """
    df_children["Expansion_Factor"] = df_individual[df_individual[f"出生有フラグ{birth_year}"] == 1]["Expansion_Factor"].tolist()
    
    return df_children

def min_child_age_update(person_id, min_age, dic_id_age):
    if(dic_id_age.get(person_id) == None):
        return min_age
    else:
        return dic_id_age.get(person_id)


def birth(df_individual, df_marrige, df_birth, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前の年を作っておく """
    period = 1
    year1pb = year - period
        
    """ # step1 : 対象年次の有配偶者出生率の計算  """

    """ # シミュレーション該当年間の出生率をデータフレームから抽出しておく """
    birth_rate = df_birth[(df_birth["西暦"] >= year1pb) & (df_birth["西暦"] < year)].reset_index(drop = True)

    """ # 有配偶者データとマージする """
    birth_rate = pd.merge(birth_rate, df_marrige, left_on = ["年齢"], right_on = [f"Age{year}"], how = "left")
    
    """ # 有配偶者出生率の計算 """
    birth_rate[f"有配偶者出生率{year}"] = birth_rate["出生率"] / birth_rate["有配偶率"]
    
    """ # 15歳にNaNが出てるので、一応埋めておく """
    birth_rate = birth_rate.fillna(0)
    
    """ # 出力 """
    # birth_rate.to_csv(rf"{root_out}/有配偶者出生率_{year}.csv", index = False, encoding = "cp932")

    """ # step2 : 個人データに対して出生判定 """

    """ # 列の選別 """
    birth_rate = birth_rate[[f"Age{year}", f"有配偶者出生率{year}"]]
    
    """ # 個人データにマージする """
    df_individual = pd.merge(df_individual, birth_rate, on = [f"Age{year}"], how = "left")
    
    """ # NaNを0で埋める → 出生率表に無い年齢とかがあり得るので """
    df_individual[f"有配偶者出生率{year}"] = df_individual[f"有配偶者出生率{year}"].fillna(0)
    
    """ # 更新期間内で毎年出生の計算をする """
    for i in range(1, period + 1):
        birth_year = year1pb + i
        
        """ # 出生判定用乱数列作成 """
        df_individual[f"出生用乱数{birth_year}"] = pd.Series(np.random.random(len(df_individual)), index = df_individual.index)

        """ # 出生判定用乱数をケース間で固定したいこころみ """
        np.random.seed(year)
        randlist = np.random.random(10000000)
        df_individual[f"出生用乱数{year}"] = df_individual["Personal_UniqueId"].apply(lambda x:randlist[x])


        """ # カテゴリと乱数列から出生判定を行う """
        df_individual[f"出生有フラグ{birth_year}"] = pd.Series(np.vectorize(birth_flag)
                                                         (df_individual[f"Marital_Status_Family_Position{year}"], 
                                                          df_individual[f"有配偶者出生率{year}"], 
                                                          df_individual[f"出生用乱数{birth_year}"]))
        
        """ # 対象年(= birth_year)の出生数 = 出生有フラグが 1 (=出生のあった個人) """
        nbirth = df_individual[f"出生有フラグ{birth_year}"].sum()
        print(f"number of birth at {year} : {nbirth}")
                
        """ # 出生者に属性を付与する """
        df_children = add_properties(df_individual, nbirth, year, birth_year, year1pb)
        
        """ # 新しい出生者のデータフレームを結合する """
        df_individual = pd.concat([df_individual, df_children])
        
        # """ # 最小子供年齢の更新 """
        # dic_min_child_age = dict(zip(df_individual[df_individual[f"出生有フラグ{birth_year}"] == 1]["個人ID"], df_children[f"世帯票_年齢{year}"]))
        # df_individual[f"最小子供年齢{year}"] = pd.Series(np.vectorize(min_child_age_update)
        #                                            (df_individual["個人ID"], 
        #                                             df_individual[f"世帯内最小年齢{year}"], 
        #                                             dic_min_child_age))
        
        """ # indexでソートしておく """
        df_individual = df_individual.sort_index()
    
    """ # 出力 """
    # df_individual.to_csv(rf"{root_out}/出生モデル_{year}.csv", index = False, encoding = "cp932")
    
    return df_individual
