# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 18:18:11 2023

@author: ktakahashi
"""

import os
import sys

import random

import numpy as np
import pandas as pd

import pickle

import functions.compress as fcp



def flag_closest_sample_to_target(df, target):
    
    # データフレームをランダムにシャッフル
    shuffled_df = df.sample(frac=1).reset_index(drop=True)
    shuffled_df['cumsum'] = shuffled_df['Expansion_Factor'].cumsum()
    
    # ターゲットを超える前のデータを取得
    before_target_df = shuffled_df[shuffled_df['cumsum'] <= target]
    
    # ターゲットを超えた後のデータを取得
    after_target_index = shuffled_df[shuffled_df['cumsum'] > target].index[0]
    after_target_df = shuffled_df.loc[:after_target_index]
    
    # どちらがターゲットに近いかを比較
    diff_before = target - before_target_df['Expansion_Factor'].sum()
    diff_after = after_target_df['Expansion_Factor'].sum() - target
    
    # 選ばれた個人の個人IDのリストを返す
    selected_uids = before_target_df['Personal_UniqueId'].values if diff_before <= diff_after else after_target_df['Personal_UniqueId'].values
    
    return selected_uids


def income_outgoing_model(df_individual, dict_prms, migrate, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # 1期前 """
    period = 1
    year1pb = year - period
        
    """ # 転入・転出率の変化率を受ける """
    """ # 割合に変換する : 20 → 120 → 1.2 """
    migrate_out = (migrate.loc[0, "Migration_Rate_Out"] + 100) / 100
    migrate_in = (migrate.loc[0, "Migration_Rate_In"] + 100) / 100
    if(migrate_out < 0 or migrate_in < 0):
        print("Migration_Rate is negative !!")
        print("acceptable value is over -100")
        print("Please check the value !!")
        sys.exit(0)
    
    """ # まずは転出 """
    combination_counts = df_individual.groupby(['Gender', f'Age_Group{year}'], as_index = False).agg({"Expansion_Factor":"sum"})

    """ # 転出率を受ける """
    outgoing_rate_df = dict_prms["転出率"].copy()
    outgoing_rate_df = outgoing_rate_df.rename(columns = {"Age_Group":f"Age_Group{year}"})
    
    """ # 転出率に変化率をかける """
    outgoing_rate_df["Outgoing_Rate"] *= migrate_out

    """ # Outgoing_Rate.csvからGenderとAge_Groupの組み合わせに対応するOutgoing_Rateの値を取得 """
    result_df = pd.merge(combination_counts, outgoing_rate_df, on=['Gender', f'Age_Group{year}'], how='left')

    """ # 数とOutgoing_Rateを掛け算し、結果を四捨五入 """
    result_df['Result'] = (result_df['Expansion_Factor'] * result_df['Outgoing_Rate']).round() /5 # 転出率は5年間の転出率なので 
    
    """ # OutgoingFlgを0で初期化 """
    df_individual['OutgoingFlg'] = 0
    
    """ # 選出者にOutgoingFlgを設定 """
    for _, row in result_df.iterrows():
        gender = row['Gender']
        age_group = row[f'Age_Group{year}']
        count = int(row['Result'])

        """ # 当該性年齢の個人を取り出す """
        selected_data = df_individual[(df_individual['Gender'] == gender) & (df_individual[f'Age_Group{year}'] == age_group)]

        """ # 転出人口の分だけサンプリング """
        selected_uids = flag_closest_sample_to_target(selected_data, count)

        """ # 選出者にOutgoingFlgを設定 """
        df_individual.loc[df_individual['Personal_UniqueId'].isin(selected_uids), "OutgoingFlg"] = 1
    
    # """ # 出力 """
    # df_individual.to_csv(rf"{root_out}/転出モデル{year}.csv", index = False, encoding = "cp932")

    """ # 転出者を除外 """
    df_outgo = df_individual[df_individual["OutgoingFlg"] == 1]
    if(os.path.exists(r"output_swich")):
        df_outgo.to_csv(rf"{root_out}/Outgoing_{year}.csv", index = False, encoding = "cp932")
    # fcp.save_as_zip(df_outgo, root_out, "Outgoing", year)

    df_individual = df_individual[df_individual["OutgoingFlg"] != 1].reset_index(drop = True)
    
    """ # 転入 """
    """ # 転入率と総移動者数を受ける """
    incoming_rate_df = dict_prms["転入率"].copy()
    total_outgoing_df = dict_prms["転出総数"].copy() 
    
    incoming_rate_df = incoming_rate_df.rename(columns = {"Age_Group":f"Age_Group{year}"})
    total_outgoing_df = total_outgoing_df.rename(columns = {"Age_Group":f"Age_Group{year}"})
    
    """ # 転入率に変化率をかける """
    incoming_rate_df["Incoming_Rate"] *= migrate_in
    
    """ # 対象年次に絞る """
    total_outgoing_df_ex = total_outgoing_df[total_outgoing_df['Year'] == year]

    # Incoming_RateとNumber_of_Outgoing_Peopleを結合
    merged_df = pd.merge(incoming_rate_df, total_outgoing_df_ex, on=['Gender', f'Age_Group{year}'], how='inner')

    # 積を計算して四捨五入
    merged_df['Result'] = (merged_df['Incoming_Rate'] * merged_df['Number_of_Outgoing_People']).round() /5 # 転出総数も五年間の数字なので

    # ランダム選出を行う部分の追加
    random_selection_df = pd.DataFrame(columns=merged_df.columns)
    
    for _, row in merged_df.iterrows():
        gender = row['Gender']
        age_group = row[f'Age_Group{year}']
        count = int(row['Result'])

        """ # 当該性年齢の個人を取り出す """
        selected_data = df_individual[(df_individual['Gender'] == gender) & (df_individual[f'Age_Group{year}'] == age_group)]

        """ # 転出人口の分だけサンプリング """
        selected_uids = flag_closest_sample_to_target(selected_data, count)
        selected_data = selected_data.loc[selected_data['Personal_UniqueId'].isin(selected_uids)]
        
        if(len(selected_data) == 0):
            random_selection_df = random_selection_df
        elif(len(random_selection_df) == 0):
            random_selection_df = selected_data
        else:
            random_selection_df = pd.concat([random_selection_df, selected_data])
        
    # random_selection_dfにPersonal_UniqueId列を追加して連番を付与
    max_personal_id = df_individual['Personal_UniqueId'].max()  # 最大値を取得
    random_selection_df['Personal_UniqueId'] = range(max_personal_id + 1, max_personal_id + 1 + len(random_selection_df))
    
    # individual_dfにIncomingFlg列を追加し、0で初期化
    df_individual['IncomingFlg'] = 0
    
    # random_selection_dfにIncomingFlg列を追加し、1で初期化
    random_selection_df['IncomingFlg'] = 1
    # random_selection_df.to_csv(rf"{root_out}/転入{year}.csv", index = False, encoding = "cp932")
        
    # individual_dfとrandom_selection_dfを結合
    col_list = ["Personal_UniqueId", f"zone_code{year1pb}", "Gender", f"Age{year}", "Expansion_Factor", 
                f"Marital_Status{year}", f"Family_Position{year}", f"Marital_Status_Family_Position{year}",
                f"Age_Group{year}", f"Marital_Status_Family_Position{year1pb}", 'IncomingFlg']
    combined_df = pd.concat([df_individual[col_list], random_selection_df[col_list]], ignore_index = True)
    
    if(os.path.exists(r"output_swich")):
        combined_df.to_csv(rf"{root_out}/Incoming_{year}.csv", index = False, encoding = "cp932")
    # fcp.save_as_zip(combined_df, root_out, "Incoming_", year)

    return combined_df
