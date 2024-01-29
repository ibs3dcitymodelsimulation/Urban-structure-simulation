# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 11:04:54 2023

@author: ktakahashi
"""

import os
import sys

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

import pickle
import functions.compress as fcp

# 前処理を行う関数
def preprocess(df):
    # ゾーンペアを作成し、すべての組み合わせを作成
    zonelist = set(list(df["zone_code_o"].unique())+list(df["zone_code_d"].unique()))
    zone_pair = pd.DataFrame([(i, j) for i in zonelist for j in zonelist], columns=['zone_code_o', 'zone_code_d'])
    # print(zone_pair)

    # ゾーンペアと結合、0うめ
    df = pd.merge(zone_pair, df, on=["zone_code_o", "zone_code_d"], how="left")
    df = df.fillna(0)

    # Index(['zone_code_o', 'zone_code_d', 'Travel_Time_Rail', 'Waiting_Time_Rail',
    #    'Access_Time_Rail', 'Egress_Time_Rail', 'Fare_Rail', 'Travel_Time_Bus',
    #    'Waiting_Time_Bus', 'Access_Time_Bus', 'Egress_Time_Bus', 'Fare_Bus',
    #    'Travel_Time_Car', 'flg_east_o', 'flg_eastwest_o', 'flg_west_o',
    #    'flg_east_d', 'flg_eastwest_d', 'flg_west_d'],
    #   dtype='object')

    # 鉄道、バス、自動車の総所要時間
    df["Total_Travel_Time_Rail"] = df["Travel_Time_Rail"] + df["Waiting_Time_Rail"] + df["Access_Time_Rail"] + df["Egress_Time_Rail"]
    df["Total_Travel_Time_Bus"] = df["Travel_Time_Bus"] + df["Waiting_Time_Bus"] + df["Access_Time_Bus"] + df["Egress_Time_Bus"]
    df["Total_Travel_Time_Car"] = df["Travel_Time_Car"]

    # 公共交通所要時間を鉄道所要時間で置き換える
    df["Total_Travel_Time_Transit"] = np.minimum(df["Total_Travel_Time_Rail"], df["Total_Travel_Time_Bus"])

    # zone_code_Oとzone_code_Dが同じ場合は、総所要時間を0に設定
    df.loc[df["zone_code_d"]==df["zone_code_o"], "Total_Travel_Time_Transit"] = 0
    df.loc[df["zone_code_d"]==df["zone_code_o"], "Total_Travel_Time_Car"] = 0

    return df

# ゾーンデータを準備する関数
def prepare_zone(df, df_acc):
    # ゾーン一覧を作成
    zone = pd.DataFrame(df['zone_code_d'].unique(), columns=['zone_code_d']).rename(columns={"zone_code_d":"zone_code"})
    # 左結合して、nullを0で埋める
    df_acc = zone.merge(df_acc, on="zone_code", how="left")
    return df_acc

# ACCを計算する関数
def calculate_exp(df, df_acc, column_name_in, column_name_out, time_column, join_on='zone_code'):
    # データフレームのコピーを作成
    df = df.copy()
    df_acc = df_acc.copy()
    
    # df_accを左結合
    grouped_df = df.merge(df_acc, left_on="zone_code_d", right_on=join_on, how='left')
    
    # expをつけて計算する
    if column_name_out == 'ACC_transit':        
        beta = -0.016938303
    else:
        beta = -0.010864028

    grouped_df[column_name_out] = grouped_df[column_name_in] * np.exp( beta*grouped_df[time_column] )
    
    # 集計
    grouped_df = grouped_df.groupby('zone_code_o', as_index=False).agg({column_name_out: 'sum'})
    
    # 列名を直す
    grouped_df = grouped_df.rename(columns={"zone_code_o":"zone_code"})
    
    return grouped_df


def calc_floorarea_1f(usage, footprint, stflag):
    params = { 402 : 0.66914, # 商業施設
               404 : 0.66914, # 商業系複合施設
               411 : 0.64974, # 住宅
               412 : 0.95940, # 共同住宅
               413 : 0.50458, # 店舗等併用住宅
               414 : 0.76023, # 店舗等併用共同住宅
               }
    if(stflag == 1):
        return footprint * params.get(usage, 0)
    else:
        return 0

def calc_floorarea_2f(usage, footprint, storeys, stflag):
    params = { 402 : 0.80584, # 商業施設
               404 : 0.80584, # 商業系複合施設
               411 : 0.57567, # 住宅
               412 : 0.58833, # 共同住宅
               413 : 0.74575, # 店舗等併用住宅
               414 : 0.70918, # 店舗等併用共同住宅
               }   
    if (stflag == 1):
        return footprint * (storeys - 1) * params.get(usage, 0)
    else:
        return 0

def calc_commfloor(usage, area1f, area2f):
    if(pd.isnull(usage)):
        return 0
    elif(usage in [402, 404]):
        """ # 402 : 商業施設, 404 : 商業系複合施設 """
        return area1f + area2f
    elif(usage in [411, 412]):
        """ # 411 : 住宅, 412 : 共同住宅 """
        return 0
    elif(usage in [413, 414]):
        """ # 413 : 店舗等併用住宅, 414 : 店舗等併用共同住宅 """
        return area1f
    else:
        return 0

def calc_housefloor(usage, area1f, area2f):
    if(pd.isnull(usage)):
        return 0
    elif(usage in [402, 404]):
        """ # 402 : 商業施設, 404 : 商業系複合施設 """
        return 0
    elif(usage in [411, 412]):
        """ # 411 : 住宅, 412 : 共同住宅 """
        return area1f + area2f
    elif(usage in [413, 414]):
        """ # 413 : 店舗等併用住宅, 414 : 店舗等併用共同住宅 """
        return area2f
    else:
        return 0



def calc_accwalk(df_accw, floorarea):
    
    """ # ゾーン重心間距離テーブルのうち、一方のzone_codeに左結合 """
    df_accw = pd.merge(df_accw, floorarea, how = "left", on = ["zone_code"])
    
    """ # もう一方のzone_codeで商業延床面積を集約 """
    df_accw = df_accw.groupby(["zone_code_2"], as_index = False).agg({"商業部分延べ床面積":"sum"})
    
    """ # rename """
    df_accw = df_accw.rename(columns = {"zone_code_2":"zone_code", "商業部分延べ床面積":"ACC_walk"})

    return df_accw


def acc_compop(dfs_dict, df_individual, df_build_org, df_accw, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # コピーして使う """
    df_zone = dfs_dict["Zone"].copy()
    df_los = dfs_dict["Zone_TravelTime"].copy()
    df_build = df_build_org.copy()
    
    """ # 前処理 """
    df_los = preprocess(df_los)
    # print(df_los)
        
    """ # 1期前 """
    period = 1
    year1pb = year - period
    
    """ # 延べ床面積の計算 """
    df_build["floorarea_1F"] = pd.Series(np.vectorize(calc_floorarea_1f)
                                         (df_build[f"Usage{year1pb}"], df_build["FootprintArea"],
                                          df_build["SimTargetFlag"]))
    
    df_build["floorarea_2F"] = pd.Series(np.vectorize(calc_floorarea_2f)
                                         (df_build[f"Usage{year1pb}"], df_build["FootprintArea"],
                                          df_build[f"storeysAboveGround{year1pb}"], df_build["SimTargetFlag"]))
    
    df_build["商業部分延べ床面積"] = pd.Series(np.vectorize(calc_commfloor)
                                      (df_build[f"Usage{year1pb}"], 
                                       df_build["floorarea_1F"], df_build["floorarea_2F"]))

    df_build["住宅延床面積"] = pd.Series(np.vectorize(calc_housefloor)
                                      (df_build[f"Usage{year1pb}"], 
                                       df_build["floorarea_1F"], df_build["floorarea_2F"]))
    
    if(os.path.exists(r"output_swich")):
        df_build.to_csv(rf"{root_out}/building_面積つき_{year}.csv", index = False, encoding = "cp932")

    """ # ゾーン別住宅/商業延床面積の集計 """
    df_floor_area = df_build.groupby(["zone_code"], as_index = False).agg({"住宅延床面積":"sum","商業部分延べ床面積":"sum"})
    df_floor_area = df_floor_area.fillna(0)
    dfs_dict["ゾーン別延べ床面積"] = df_floor_area.copy()

    """ # データ出力 """
    if(os.path.exists(r"output_swich")):
        df_floor_area.to_csv(rf"{root_out}/ゾーン別商業延床面積_{year}.csv", index = False, encoding = "cp932")


    """ # ゾーン別人口 : 死亡者カテゴリ 99 は除いているので大丈夫 """
    df_pop = df_individual.groupby([f"zone_code{year1pb}"], as_index = False).agg({"Expansion_Factor":"sum"})
    df_pop = df_pop.rename(columns = {f"zone_code{year1pb}":"zone_code", "Expansion_Factor":"pop"})

    """ # ゾーンデータ準備 """
    df_floor_area = prepare_zone(df_los, df_floor_area)
    df_pop = prepare_zone(df_los, df_pop)

    # ACCを計算する　列名は適宜修正ください
    # 商業部分延べ床面積は、昨年と同じルールで建築物データから作成。つまり、商業施設は全延べ床、店舗併用〇〇は1F部分のみの延べ床を、ゾーン単位で足す。
    ACC_transit = calculate_exp(df_los, df_floor_area, "商業部分延べ床面積", "ACC_transit", "Total_Travel_Time_Transit")
    ACC_car = calculate_exp(df_los, df_floor_area, "商業部分延べ床面積", "ACC_car", "Total_Travel_Time_Car")
    ACC_walk = calc_accwalk(df_accw, df_floor_area)

    # ACCPを計算する　列名は適宜修正ください
    ACCP_transit = calculate_exp(df_los, df_pop, "pop", "ACCP_transit", "Total_Travel_Time_Transit")
    ACCP_car = calculate_exp(df_los, df_pop, "pop", "ACCP_car", "Total_Travel_Time_Car")
    
    """ # ゾーンデータに引っ付ける """
    df_zone = pd.merge(df_zone, ACC_transit, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, ACC_car, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, ACCP_transit, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, ACCP_car, how = "left", on = ["zone_code"])
    df_zone = pd.merge(df_zone, ACC_walk, how = "left", on = ["zone_code"])

    """ # データ出力 """
    if(os.path.exists(r"output_swich")):
        df_zone.to_csv(rf"{root_out}/ACC{year}.csv", index = False, encoding = "cp932")

    return df_zone
    