# -*- coding: utf-8 -*-
"""
Created on Tue Sep  5 10:18:15 2023

@author: ktakahashi
"""

import os
import sys

import shutil

import numpy as np
import pandas as pd

import functions.preprocess as fpp                 # 事前処理
import functions.acc_compop as acp                 # ACC, 商圏人口モデル
import functions.bidrent_model as brm              # 付け値地代モデル
import functions.house_landprice_model as hlp      # 住宅地価モデル
import functions.commercial_landprice_model as clp # 商業地価モデル
import functions.category_transition as fct        # 個人カテゴリ遷移
import functions.individual_aging as fia           # 個人加齢
import functions.marriage_rate as fmr              # 配偶率
import functions.birth as fbh                      # 出生計算
import functions.income_outgo_model as iom         # 転入転出モデル
import functions.relocation_model as frl           # 転居発生
import functions.residence_select_model as rsm     # 居住地選択
import functions.reconstruction_model as frc       # 建物除却,建設,用途選択
import functions.building_storeys_model as bsm     # 階数モデル
import functions.building_height_model as bhm      # 高さモデル
import functions.output_settings as fos
import functions.floor_area_rate as far
import functions.compress as fcp

pd.set_option("display.max_columns", 100)

def main():
    print("Function : ", sys._getframe().f_code.co_name)

    """ # Control Inputの読み込み """
    with open(r"./Control_Sim.txt", mode = "r", encoding = "cp932") as ci:
        root_inp_base = next(ci).strip()
        root_inp_scenario = next(ci).strip()
        root_out = next(ci).strip()
    
    """ # 出力先 """
    if not(os.path.exists(root_out)):
        os.makedirs(root_out)

    """ # インプットをコピーして出力先に保存 """
    if(os.path.exists(r"output_swich")):
        if not(os.path.exists(root_out+"/input")):
            os.makedirs(root_out+"/input")
        shutil.copyfile(r"./Control_Sim.txt", rf"{root_out}/input/Control_Sim.txt")
        shutil.copytree(root_inp_base, rf"{root_out}/input/BaseData")
        shutil.copytree(r"./functions", rf"{root_out}/input/functions")
        shutil.copytree(r"./Parameter", rf"{root_out}/input/Parameter")
        shutil.copytree(root_inp_scenario, rf"{root_out}/input/ScenarioData")
    
    """ # シミュレーション開始,終了年の読み込み """
    with open(rf"{root_inp_scenario}/Control_SimYear.txt", mode = "r", encoding = "cp932") as cy:
        start_year = int(next(cy).strip())
        fin_year = int(next(cy).strip())
    
    """ # Control_SimInputの読み込み """
    df_csi = pd.read_csv(os.path.join(root_inp_scenario, "Control_SimInput.csv"), 
                         encoding = "cp932", index_col = "year")
    
    csi_cols = ["Zone", "Zone_TravelTime", "Dist_Building_Station", "Land_Price_Change_Rate", "Migration_Rate"]
    
    """ # シミュレーション年次の整合チェック """
    """ # set objectにして, <= で内包チェック """
    year_csi = set(df_csi.index)
    year_csy = set(range(start_year, fin_year + 1))
    ck = year_csy <= year_csi
    if(ck == False):
        print("Error !!\n",
              "There is an inconsistency between the year listed in Control_SimYear.txt and Control_SimInput.csv.\n"
              "Please check the year listed.")
        sys.exit(0)
    
    """ # 開始時用のデータ読み込み """
    dfs_dict = {}
    for col in csi_cols:
        dfs_dict[col] = pd.read_csv(df_csi.loc[start_year, col], encoding = "cp932")
    
    """ # baseデータとパラメータの設定ファイルの読み込み """
    if(os.path.exists(r"Control_base_param.csv")):
        df_bp = pd.read_csv(r"Control_base_param.csv", encoding = "cp932")
    else:
        df_bp = fpp.default_control()

    """ # データ読み込み """
    dict_prms = fpp.data_reader(df_bp, root_inp_base, root_inp_scenario)
        
    """ # データの切り分け """
    df_build = dict_prms["建物データ"].copy()
    df_individual = dict_prms["個人データ"].copy()
    df_distfacil = dict_prms["施設別ゾーン別平均距離"].copy()
    
    """ # データを分けたので, 捨てる(重くなるから) """
    del dict_prms["建物データ"], dict_prms["個人データ"], dict_prms["施設別ゾーン別平均距離"]
    
    """ # 事前処理 """
    """ # 建物データ """
    df_build = fpp.building_data(df_build, start_year)

    """ # 240101追加 階数構成比を計算してパラメータとして上書き """
    dict_prms["階数割合"] = far.calc_floor_area_rate(df_build, dfs_dict, root_out)

    """ # 個人データ """
    df_individual = fpp.individual_data(df_individual, start_year)
    
    """ # パラメータ """
    dict_prms["遷移確率"], df_trans_keys, agerank_max = fpp.pp_transitionprob(dict_prms["遷移確率"])
    dict_prms["転入率"] = fpp.pp_income_outgo(dict_prms["転入率"])
    dict_prms["転出率"] = fpp.pp_income_outgo(dict_prms["転出率"])
    dict_prms["転出総数"] = fpp.pp_income_outgo(dict_prms["転出総数"])
        
    """ # 平均と標準偏差を、シミュレーション実施前に計算しておく """
    """ # 住宅地価の平均と標準偏差 """
    dict_prms["住宅地価平均標準偏差"], tmp = fpp.calc_landprice_meanstd(dict_prms["公示地価データ"], dict_prms["地価調査データ"], "住宅地価", root_out)
    dict_prms["商業地価平均標準偏差"], dict_prms["商業地価データ"] = fpp.calc_landprice_meanstd(dict_prms["公示地価データ"], dict_prms["地価調査データ"], "商業地価", root_out)
    
    """ # BaseDataのデータを読み込む """
    dfs_dict["Zone"] = pd.read_csv(rf"{root_inp_base}/Zone.csv", encoding = "cp932")
    dfs_dict["Zone_TravelTime"] = pd.read_csv(rf"{root_inp_base}/Zone_TravelTime.csv", encoding = "cp932")

    """ # ACC/商圏人口作成 """
    dfs_dict["Zone"] = acp.acc_compop(dfs_dict, df_individual, df_build, dict_prms["zone重心間800mペア"], start_year + 1, root_out)
    
    """ # 変数の標準化 """
    dfs_dict = fpp.set_stdmean(dfs_dict, df_distfacil, df_individual, start_year, root_out)

    """ # 年次のループ """
    for year in range(start_year + 1, fin_year + 1):
        print("Simulation at ", year)
        
        """ # 年次別に変化するデータの読み込み判定 """
        for col in csi_cols:
            npath = df_csi.loc[year, col]
            ppath = df_csi.loc[year - 1, col]
            if(ppath != npath)or(year == start_year + 1):
                dfs_dict[col] = pd.read_csv(npath, encoding = "cp932")

        """ # ACC/商圏人口作成 """
        dfs_dict["Zone"] = acp.acc_compop(dfs_dict, df_individual, df_build, dict_prms["zone重心間800mペア"], year, root_out)
                
        """ # 付け値地代モデル """
        dfs_dict["Zone"] = brm.bidrent_model(dfs_dict, df_distfacil, dict_prms, year, root_out)
        
        """ # 住宅地価モデル """
        dfs_dict["Zone"] = hlp.house_landprice_model(dfs_dict, df_individual, dict_prms, year, root_out)

        """ # 商業地価モデル """
        df_build = clp.commercial_landprice_model(dfs_dict, df_build, dict_prms, year, root_out, year == start_year+1)
        
        """ # カテゴリ遷移 """
        df_individual = fct.category_transition(df_individual, dict_prms["遷移確率"], year, root_out)
        
        """ # 個人データ加齢 """
        df_individual = fia.aging(df_individual, year, agerank_max)
        
        """ # 年齢別有配偶率計算 """
        df_marrige = fmr.marriage_rate(df_individual, year, root_out)

        """ # 出生計算 """
        df_individual = fbh.birth(df_individual, df_marrige, dict_prms["出生率"], year, root_out)
        
        """ # 転入転出 """
        df_individual = iom.income_outgoing_model(df_individual, dict_prms, dfs_dict["Migration_Rate"], year, root_out)
        
        """ # 転居発生 """
        df_individual = frl.relocation_model(df_individual, dict_prms["転居発生パラメータ"], year, root_out)
        
        """ # 居住地選択 """
        df_individual = rsm.residence_select_model(df_individual, dfs_dict, dict_prms, year, root_out)

        """ # 建設,除却,用途選択 """
        df_build = frc.reconstruction_model(dfs_dict["Zone"], df_build, dfs_dict["Land_Price_Change_Rate"], dict_prms, year, root_out)
        
        """ # 階数モデル """
        df_build = bsm.storeys_model(df_build, dict_prms, year, root_out)
        
        """ # 高さモデル """
        df_build = bhm.building_height_model(df_build, dict_prms, year, root_out)
                
        """ # 出力調整 """
        df_individual, df_build, dfs_dict["Zone"] = fos.output(df_individual, df_build, dfs_dict["Zone"], year, root_out)

    
    """ # 圧縮 """
    fcp.compression(root_out)

    print("Finished !!")


if(__name__ == "__main__"):
    main()