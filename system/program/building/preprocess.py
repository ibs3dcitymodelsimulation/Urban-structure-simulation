# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def zone_sort(df):
    
    """ # Rは()が.になってしまうので、置き換えておく """
    newcolname = [c.replace("(","_").replace(")","")  for c in df.columns]
    df.columns = newcolname
    
    """ # 面積データも別読みしておく方が取り回しが良い """
    """ # 人口データはライフイベントで変わるので、読みこんでも仕方ないので落とす """
    """ # 商業・住宅延べ床面積も別読みの方が取り回しが良い """
    """ # 到達可能圏域人口も入ってるけど、ライフイベントで集計することになるので、落としておく """
    df = df.drop(["pop_all", "AREA", "farea_residence"], axis = 1)

    """ # ゾーンコードをソートする """
    df = df.sort_values("zone_code").reset_index(drop = True)
    
    """ # ここでタミー変数を入れておいていい """
    dummylist = ["第一種低層住居専用地域","第二種低層住居専用地域","第一種中高層住居専用地域","第二種中高層住居専用地域"]
    df["j_senyo"] = df["yotochiki"].apply(lambda x: 1 if x in dummylist else 0)

    dummylist = ["第一種住居地域","第二種住居地域","準住居地域"]
    df["j_tiki"] = df["yotochiki"].apply(lambda x: 1 if x in dummylist else 0)
    
    dummylist = ["商業地域","近隣商業地域"]
    df["s_tiki"] = df["yotochiki"].apply(lambda x: 1 if x in dummylist else 0)

    return df

def pp_zone_data(df, col_list):
    """ # ゾーン別データのうち、残すものを選択する """
    left_list = ["zone_code"] + col_list
    df = df[left_list]
    
    return df

def pp_brm_prm(df):
    """ # 3列目が要らないので落とす """
    df = df.drop(df.columns[[2]], axis = 1)
    
    """ # 1列目をindexに指定しなおす """
    df = df.set_index("variable")
    
    return df

def pp_hlm_prm(df):

    """ # 不要な行を落とす """
    df = df.drop([7,8])

    """ # 1列目をindexに指定しなおす """
    df = df.set_index("variable")
    
    return df
    
def pp_clm_prm(df):
    """ # 1列目をindexに指定する """
    df = df.set_index("variable")
    
    return df

def pp_sm_prm1(df):
    """ # 5行目がいらない """
    df = df.drop([2, 3])
    
    """ # 3列目がいらない """
    df = df.drop(df.columns[[2]], axis = 1)

    """ # 1列目をindexに指定しなおす """
    df = df.set_index("variable")
    
    return df

def add_usage_group(yotochiki):
    if(yotochiki in ["第一種低層住居専用地域","第一種中高層住居専用地域","第二種中高層住居専用地域"]):
        return "G1"
    elif(yotochiki in ["第一種住居地域","第二種住居地域","準住居地域"]):
        return "G2"
    elif(yotochiki in ["近隣商業地域","商業地域"]):
        return "G3"
    else:
        return "G4"
    
def pp_buildingdata(df, year):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 用途地域にコード番号をふる """
    dic_usagecode = {"第一種低層住居専用地域":1, "第二種低層住居専用地域":2, "第一種中高層住居専用地域":3, "第二種中高層住居専用地域":4,
                     "第一種住居地域":5, "第二種住居地域":6, "準住居地域":7, "近隣商業地域":8,
                     "商業地域":9, "準工業地域":10, "工業地域":11, "工業専用地域":12}
    df["usage_code"] = df["yotochiki"].map(dic_usagecode)
    df["usage_code"] = df["usage_code"].fillna(99)
    # col_inp.append("usage_code")
    
    """ # 用途地域グループを追加する """
    df["usage_group"] = pd.Series(np.vectorize(add_usage_group)(df["yotochiki"]))


    """ # 年次を追記する列名 """
    col_add = ["building_age", "yoto", "existing", "display_high_median", "storey", "floorarea"]
    
    """ # inputにある列名を保存しておくリスト """
    col_inp = []
    
    """ # シミュレーション開始年を列名に追記する """
    col_dic = {}
    for col in df.columns.values:
        if(col in col_add):
            col_dic[col] = col + str(year)
        else:
            """ # 年次を追加しない列を保存しておく """
            col_inp.append(col)
    df = df.rename(columns = col_dic)
    

    return df, col_inp
    
def pp_addrand(df, year):
    # print("Function : ", sys._getframe().f_code.co_name)
    
    df[f"建て替え判定用乱数{year}"] = pd.Series(np.random.random(len(df)), index = df.index)
    
    return df

def pp_building_status(df, year):
    print("Function : ", sys._getframe().f_code.co_name)
    
    df = df[["tatemono_code", f"existing{year}"]].copy()
    df["変遷フラグ"] = "入力値"
    
    """ # 判定用の列もここで作っておく """
    df["num_exist"] = 0
    df["num_remove"] = 0
    df["num_build"] = 0
    
    """ # 並び替え """
    df = df[["tatemono_code", "変遷フラグ", "num_exist", "num_remove", "num_build", f"existing{year}"]]
    
    return df
    

