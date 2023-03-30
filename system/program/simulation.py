# -*- coding: utf-8 -*-

import os
import sys

import tqdm

import numpy as np
import pandas as pd


import submodule.read_initial as ri
import submodule.convert_cityGML as sub_gml

""" # ライフイベント系モジュール ここから """
import life_event.preprocess as le_pre
import life_event.category_transition as le_ct
import life_event.aging as le_age
import life_event.marriage_rate as le_mr
import life_event.birth as le_birth
import life_event.relocation_model as le_rlm
import life_event.residence_select_model as le_rsm
import life_event.zone_pop_update as le_zpu
import life_event.postprocess as le_po
""" # ライフイベント系モジュール ここまで """

""" # 建物系モジュール ここから """
import building.preprocess as b_pre
import building.bid_rent_model as b_brm
import building.house_landprice_model as b_hlm
import building.commercial_landprice_model as b_clm
import building.removing_model as b_rm
import building.construction_model as b_cm
import building.building_usage_selection_model as b_busm
import building.aging as b_age
import building.storeys_model as b_sm
import building.floorarea_model as b_fa
import building.building_height_model as b_height
import building.cfa_update as b_cfup
import building.building_status as b_status
import building.vacant_building_model as b_vbm
import building.post_process as b_po
""" # 建物系モジュール ここまで """

def location_simulator(df_set, df_control, df_outset):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ 
        # まずはファイルをデータフレームに読み込み 
        # 辞書にして持っておく
    """
    dfs_dict = {}
    for i in range(len(df_control)):
        id_key = df_control.index.values[i]
        dfs_dict[id_key] = ri.read_input(df_control.loc[id_key, "ファイル名"])
    
    """ # パラメータファイルの事前処理 """
    """ # 遷移確率 """
    """ # return : 遷移確率事前処理後, 遷移確率キー, 年齢階層の最大値 """
    dfs_dict["遷移確率"], df_trans_keys, agerank_max = le_pre.pp_transitionprob(dfs_dict["遷移確率"])

    """ # 個人データの列名にシミュレーション開始年を追記しておく """
    dfs_dict["個人データ"] = le_pre.pp_individual(dfs_dict["個人データ"], df_set.loc["開始年", "設定値"])

    dfs_dict["転居発生モデルパラメータ"] = le_pre.pp_prmfile(dfs_dict["転居発生モデルパラメータ"])
    dfs_dict["居住地選択モデルパラメータ"] = le_pre.pp_prmfile(dfs_dict["居住地選択モデルパラメータ"])
    dfs_dict["居住地選択モデル標準化パラメータ"] = le_pre.pp_prmfile(dfs_dict["居住地選択モデル標準化パラメータ"])

    dfs_dict["ゾーンデータ"] = b_pre.zone_sort(dfs_dict["ゾーンデータ"])
    dfs_dict["ゾーン別延べ床面積"] = b_pre.pp_zone_data(dfs_dict["ゾーン別延べ床面積"], ["farea_residence", "farea_shop"])
    dfs_dict["ゾーン別人口"] = b_pre.pp_zone_data(dfs_dict["ゾーン別人口"], ["pop_all"])
    dfs_dict["ゾーン別面積"] = b_pre.pp_zone_data(dfs_dict["ゾーン別面積"], ["AREA"])
    dfs_dict["建物データ"], col_inp = b_pre.pp_buildingdata(dfs_dict["建物データ"], df_set.loc["開始年", "設定値"])
    dfs_dict["建物データ_入力値"] = dfs_dict["建物データ"].copy()

    dfs_dict["付け値地代モデルパラメータ"] = b_pre.pp_clm_prm(dfs_dict["付け値地代モデルパラメータ"]) # ← パラメータファイルを差し替えて処理関数を変更
    dfs_dict["付け値地代モデル主成分"] = b_pre.pp_clm_prm(dfs_dict["付け値地代モデル主成分"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["付け値地代モデル標準化パラメータ"] = b_pre.pp_clm_prm(dfs_dict["付け値地代モデル標準化パラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["住宅地価モデルパラメータ"] = b_pre.pp_hlm_prm(dfs_dict["住宅地価モデルパラメータ"])
    dfs_dict["商業地価モデルパラメータ"] = b_pre.pp_clm_prm(dfs_dict["商業地価モデルパラメータ"])
    dfs_dict["除却有無モデルパラメータ"] = b_pre.pp_clm_prm(dfs_dict["除却有無モデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["建設有無モデルパラメータ"] = b_pre.pp_brm_prm(dfs_dict["建設有無モデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["用途選択モデルパラメータ"] = b_pre.pp_brm_prm(dfs_dict["用途選択モデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["階数選択モデルパラメータ"] = b_pre.pp_sm_prm1(dfs_dict["階数選択モデルパラメータ"])
    dfs_dict["延べ床面積モデルパラメータ"] = b_pre.pp_clm_prm(dfs_dict["延べ床面積モデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["建物高さモデルパラメータ"] = b_pre.pp_clm_prm(dfs_dict["建物高さモデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし
    dfs_dict["空家モデルパラメータ"] = b_pre.pp_brm_prm(dfs_dict["空家モデルパラメータ"]) # ← 必要な処理が同じなので関数を使いまわし

    dfs_dict["建物変遷データ"] = b_pre.pp_building_status(dfs_dict["建物データ"], df_set.loc["開始年", "設定値"])
    """ # 事前処理 終了 """
    
    """ # 時間経過スタート """
    start = df_set.loc["開始年", "設定値"] + df_set.loc["間隔", "設定値"]
    fin = df_set.loc["終了年", "設定値"] + df_set.loc["間隔", "設定値"]
    step = df_set.loc["間隔", "設定値"]
    for year in tqdm.tqdm(range(start, fin, step)):
        print(f"\nsimulation year = {year}")
        
        """ # 乱数シードの設定 """
        ri.set_randomseed(df_set.loc["乱数シード", "設定値"], year)
        
        """ # 地価系 """
        """ # 付け値地代モデル """
        dfs_dict["付け値地代"] = b_brm.bid_rent_model(dfs_dict["ゾーンデータ"], 
                                                 dfs_dict["付け値地代モデルパラメータ"], 
                                                 dfs_dict["付け値地代モデル主成分"], 
                                                 dfs_dict["付け値地代モデル標準化パラメータ"],
                                                 year, 
                                                 df_outset.loc["付け値地代モデル", :])

        """ # 住宅地価モデル """
        dfs_dict["住宅地価"] = b_hlm.house_landprice_model(dfs_dict["付け値地代"], 
                                                       dfs_dict["ゾーン別人口"], 
                                                       dfs_dict["ゾーン別面積"], 
                                                       dfs_dict["ゾーン別延べ床面積"],
                                                       dfs_dict["住宅地価モデルパラメータ"], 
                                                       year, df_outset.loc["住宅地価モデル", :])
        
        """ # 商業地価モデル """
        dfs_dict["商業地価"] = b_clm.commercial_landprice_model(dfs_dict["ゾーンデータ"], 
                                                            dfs_dict["ゾーン別人口"], 
                                                            dfs_dict["公共交通到達可能圏域(20分)"], 
                                                            dfs_dict["公共交通到達可能圏域(40分)"], 
                                                            dfs_dict["自動車到達可能圏域"], 
                                                            dfs_dict["商業地価モデルパラメータ"], 
                                                            year,
                                                            df_outset.loc["商業地価モデル", :])

        """ # ライフイベント系 """
        """ # カテゴリ遷移 """
        dfs_dict["個人データ"] = le_ct.category_transition(dfs_dict["個人データ"], 
                                                      dfs_dict["遷移確率"], 
                                                      year, 
                                                      step, 
                                                      df_outset.loc["カテゴリ遷移モデル", :])
        
        """ # 加齢 """
        dfs_dict["個人データ"] = le_age.aging(dfs_dict["個人データ"], 
                                         year, 
                                         step, 
                                         agerank_max)
        
        """ # 年齢別有配偶率計算 """
        dfs_dict["有配偶者データ"] = le_mr.marriage_rate(dfs_dict["個人データ"], 
                                                  year, 
                                                  df_outset.loc["有配偶率", :])
        
        """ # 出生計算 """
        dfs_dict["個人データ"] = le_birth.birth(dfs_dict["個人データ"], 
                                           dfs_dict["有配偶者データ"], 
                                           dfs_dict["出生率"], 
                                           year, 
                                           step, 
                                           df_outset.loc["有配偶者出生率", :], 
                                           df_outset.loc["出生モデル", :])
        
        """ # 転居系 """        
        """ # 転居発生有無モデル """
        dfs_dict["個人データ"] = le_rlm.relocation_model(dfs_dict["個人データ"],  
                                                    dfs_dict["転居発生モデルパラメータ"], 
                                                    year, step, 
                                                    df_outset.loc["転居発生有無モデル", :])
        
        """ # 居住地選択モデル """
        dfs_dict["個人データ"] = le_rsm.residence_select_model(dfs_dict["個人データ"], 
                                                          dfs_dict["ゾーンデータ"], 
                                                          dfs_dict["付け値地代"],
                                                          dfs_dict["住宅地価"],
                                                          dfs_dict["ゾーン別延べ床面積"],
                                                          dfs_dict["地価変化率"],
                                                          dfs_dict["居住地選択モデルパラメータ"], 
                                                          dfs_dict["居住地選択モデル標準化パラメータ"],
                                                          year, step, 
                                                          df_outset.loc["居住地選択モデル", :],
                                                          df_outset.loc["ゾーン別選択確率", :])
        
        """ # ゾーン別人口更新 """
        dfs_dict["ゾーン別人口"] = le_zpu.zone_pop_update(dfs_dict["個人データ"], 
                                                    year, 
                                                    df_outset.loc["年次別ゾーン別人口",:])
        
        """ # 個人データ整理 """
        dfs_dict["個人データ"] = le_po.postprocess(dfs_dict["個人データ"], 
                                              year, 
                                              step, 
                                              #df_outset.loc["年次別個人データ", :]
                                              df_outset.loc["annual_individual_data", :])


        """ # 建て替えモデル系 """
        """ # 除却有無モデル """
        dfs_dict["建物データ"] = b_rm.removing_model(dfs_dict["建物データ"], 
                                                dfs_dict["除却有無モデルパラメータ"], 
                                                year, 
                                                step, 
                                                df_outset.loc["除却有無モデル", :])

        """ # 用途選択ログサム計算 """
        dfs_dict["用途選択ログサム"] = b_busm.calc_usagelgsm(dfs_dict["建物データ"], 
                                                     dfs_dict["用途選択モデルパラメータ"], 
                                                     dfs_dict["住宅地価"], 
                                                     dfs_dict["商業地価"],
                                                     dfs_dict["地価変化率"],
                                                     year, 
                                                     step, 
                                                     df_outset.loc["用途選択ログサム", :])

        """ # 建設有無モデル """
        dfs_dict["建物データ"] = b_cm.construction_model(dfs_dict["建物データ"], 
                                                    dfs_dict["建設有無モデルパラメータ"], 
                                                    dfs_dict["用途選択ログサム"],
                                                    year, 
                                                    step, 
                                                    df_outset.loc["建設有無モデル", :])
        
        """ # 用途選択モデル """
        dfs_dict["建物データ"] = b_busm.building_usage_selection_model(dfs_dict["建物データ"], 
                                                                  dfs_dict["用途選択ログサム"],
                                                                  year, 
                                                                  step, 
                                                                  df_outset.loc["用途選択モデル", :])

        """ # 建物の年齢を追加する """
        dfs_dict["建物データ"] = b_age.aging(dfs_dict["建物データ"], 
                                        year, 
                                        step, 
                                        df_outset.loc["建物年齢モデル", :])

        """ # 階数モデル """
        dfs_dict["建物データ"] = b_sm.storeys_model(dfs_dict["建物データ"], 
                                               dfs_dict["階数割合データ"], 
                                               dfs_dict["階数選択モデルパラメータ"], 
                                               year, 
                                               step,
                                               df_outset.loc["階数モデル", :])

        """ # 延べ床面積モデル """
        dfs_dict["建物データ"] = b_fa.floor_area_model(dfs_dict["建物データ"], 
                                                  dfs_dict["延べ床面積モデルパラメータ"],
                                                  year, 
                                                  step, 
                                                  df_outset.loc["延べ床面積モデル", :])
        
        """ # 建物高さモデル """
        dfs_dict["建物データ"] = b_height.building_height_model(dfs_dict["建物データ"], 
                                                           dfs_dict["建物高さモデルパラメータ"], 
                                                           year, 
                                                           step, 
                                                           df_outset.loc["建物高さモデル", :])
        
        """ # 延べ床面積の更新 """
        dfs_dict["ゾーン別延べ床面積"] = b_cfup.cfa_update(dfs_dict["建物データ"], 
                                                  year, 
                                                  df_outset.loc["年次別建物面積", :])
        
        """ # 建築状態のファイル作成・更新 """
        dfs_dict["建物変遷データ"] = b_status.building_status(dfs_dict["建物データ"], 
                                                       dfs_dict["建物変遷データ"], 
                                                       year, 
                                                       df_outset.loc["変遷フラグ", :])
        
        """ # 空家モデル """
        dfs_dict["建物データ"] = b_vbm.vacant_building_model(dfs_dict["建物データ"], 
                                                        dfs_dict["ゾーンデータ"], 
                                                        dfs_dict["ゾーン別人口"], 
                                                        dfs_dict["空家モデルパラメータ"], 
                                                        year, 
                                                        step, 
                                                        df_outset.loc["ゾーン別空家数", :],
                                                        df_outset.loc["空家フラグ付与", :])
        
        
        """ # 年次別建物データの出力と整理 """
        """ # 2023/02/07 OSS用に調整 """
        """ # cityGML変換用のデータフレームを受けるように修正 """
        if(year == 2020):
            dfs_dict["建物データ"], df_gml = b_po.post_output(dfs_dict["建物データ"], 
                                                         dfs_dict["建物変遷データ"], 
                                                         year, 
                                                         step, 
                                                         col_inp, 
                                                         df_set.loc["推計外建物データの付与", "設定値"], 
                                                         dfs_dict["推計対象外建物データ1"],
                                                         #df_outset.loc["年次別建物データ", :]
                                                         df_outset.loc["annual_building_data", :])
        else:
            dfs_dict["建物データ"], df_gml = b_po.post_output(dfs_dict["建物データ"], 
                                                         dfs_dict["建物変遷データ"], 
                                                         year, 
                                                         step, 
                                                         col_inp, 
                                                         df_set.loc["推計外建物データの付与", "設定値"], 
                                                         dfs_dict["推計対象外建物データ2"],
                                                         #df_outset.loc["年次別建物データ", :]
                                                         df_outset.loc["annual_building_data", :])

            """ # cityGML用にデータ変換 """
            """ # 変遷フラグのベースが2020年なので、それ以降でないと対応できない """
            sub_gml.convert_cityGML(df_gml,
                                    year,
                                    #df_outset.loc["cityGML用建物データ", :]
                                    df_outset.loc["building_data_for_cityGML", :])
            
        """ # 年次別ゾーンデータの出力 """
        b_po.post_zonedata(dfs_dict, 
                           year, 
                           df_set.loc["開始年", "設定値"], 
                           df_outset.loc["年次別建物数集計", :], 
                           #df_outset.loc["年次別ゾーンデータ", :]
                           df_outset.loc["annual_zone_data", :])
        
        """ # 建物モデルイベント終了 """
        
    """ # 時間経過終了 """

    