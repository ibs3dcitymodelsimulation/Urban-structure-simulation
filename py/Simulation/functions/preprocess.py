# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 10:38:25 2023

@author: ktakahashi
"""

import os
import sys

import numpy as np
import pandas as pd

import geopandas as gpd


def building_data(df, year):
    
    """ # 建物データ前処理 """
    
    """ # 築年数の付与 """
    """ # 建築物データ内で最も若い建物を0にして築年数を埋める。 """
    df["BuildingAge"] = df["YearOfConstruction"].max() - df["YearOfConstruction"]
    df["BuildingAge"] = df["BuildingAge"].fillna(0)
    
    """ # 適当に埋める """
    df["RoadWidth"] = df["RoadWidth"].fillna(0)

    """ # 空地の築年数と用途 """
    df.loc[df["Existing"]==2, "Usage"] = -1
    df.loc[df["Existing"]==2, "BuildingAge"] = -1
    
    """ # 年次を追加する列名 """
    col_add = ["Usage", "Height", "storeysAboveGround", "totalFloorArea", "Existing", "BuildingAge"]
    
    """ # シミュレーション開始年を列名に追記する """
    col_dic = {}
    for col in df.columns.values:
        if(col in col_add):
            col_dic[col] = col + str(year)
    df = df.rename(columns = col_dic)    
    
    return df

def individual_data(df, year):

    """ # 個人データ前処理 """    
    """ # 年次を追加する列名 """
    col_dic = {}
    for i in range(len(df.columns.values)):
        if(df.columns.values[i] not in ["Personal_UniqueId", "Gender", "Expansion_Factor"]):
            col_dic[df.columns.values[i]] = df.columns.values[i] + str(year)
    df = df.rename(columns = col_dic)    
    
    return df


""" # 遷移確率の事前処理関数 """
def pp_transitionprob(df):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 事前処理 1 : 確率が 0 以上のみに絞る """
    df = df[df["確率"] > 0].reset_index(drop = True)

    """ # 事前処理 2 : ソート """
    df = df.sort_values(["年", "性別", "年齢", "旧", "新"], ignore_index = True)

    """ # 事前処理 3 : 集計 """
    df_agg = df.groupby(["年", "性別", "年齢", "旧"], as_index = False).agg({"確率":"sum"})
    df_agg = df_agg.rename(columns = {"確率":"確率計"})

    """ # 事前処理 4 : 確率の対応付け """
    df = pd.merge(df, df_agg, on = ["年", "性別", "年齢", "旧"], validate = "m:1")

    """ # 事前処理 5 : 確率を補正 """
    df["確率補正"] = df["確率"] / df["確率計"]

    """ # 事前処理 6 : 年・性別・年齢・旧別の累積確率を計算 """
    df["累積確率"] = df.groupby(["年", "性別", "年齢", "旧"], as_index = False)["確率補正"].cumsum()

    """ # 事前処理 7 : 年齢ランクの最大値を取ってくる """
    agerank_max = df["年齢"].max()
    
    """ # キーと累積確率があればいい """
    df = df.drop(columns = ["確率", "確率計", "確率補正"])
    
    """ # キー["年", "性別", "年齢", "旧"]をユニークにしたい """
    df_keys = df[["年", "性別", "年齢", "旧"]].drop_duplicates().reset_index(drop = True)
    
    return df, df_keys, agerank_max

def pp_income_outgo(df):
    df["Gender"] = df["Gender"].replace({0:1, 1:2})
    
    return df


def default_control():
    
    """ # デフォルト設定用の辞書 """
    default_items = {"建物データ":["データ", "Building.csv"], 
                     "施設別ゾーン別平均距離":["データ", "Dist_Zone_Facility.csv"],
                     "個人データ":["データ","individual.csv"],
                     "公示地価データ":["データ", "L01-20.shp"],
                     "地価調査データ":["データ", "L02-20.shp"],
                     "zone重心間800mペア":["データ", "Zone_Centroid_Distance_Table.csv"],
                     "付け値地代パラメータ":["パラメータ", "parameter_BidRentModel.csv"],
                     "付け値地代主成分":["パラメータ", "PCscore_BidRentModel.csv"],
                     "住宅地価パラメータ":["パラメータ", "parameter_ResidentialLandPriceModel.csv"],
                     "商業地価モデル":["パラメータ", "parameter_CommercialLandPrice.pkl"],
                     "遷移確率":["パラメータ", "transition_probability.csv"],
                     "出生率":["パラメータ", "annual_age_birth_rate.csv"],
                     "転入率":["パラメータ", "Incoming_Rate.csv"],
                     "転出率":["パラメータ", "Outgoing_Rate.csv"],
                     "転出総数":["パラメータ", "Total_Outgoing_Population.csv"],
                     "転居発生パラメータ":["パラメータ", "parameter_MoveDecision.csv"],
                     "居住地選択パラメータ":["パラメータ", "parameter_ResidenceChoice.csv"],
                     "G1_prms":["パラメータ", "NLG1_NewStr_estimates.csv"],
                     "G2_prms":["パラメータ", "NLG2_NewStr_estimates.csv"],
                     "G3_prms":["パラメータ", "NLG3_NewStr_estimates.csv"],
                     "G4_prms":["パラメータ", "NLG4_NewStr_estimates.csv"],
                     "階数割合":["パラメータ", "ratio_of_number_of_floors.csv"],
                     "階数パラメータ":["パラメータ", "number_of_floors_selection_model_parameters.csv"],
                     "高さパラメータ":["パラメータ", "building_height_model_parameters.csv"]
                     }
    
    """ # データフレームに変換する """
    df = pd.DataFrame(default_items.items(), columns=["データキーワード", "設定リスト"])
    df["タイプ"] = df["設定リスト"].apply(lambda x : x[0])
    df["ファイル名"] = df["設定リスト"].apply(lambda x : x[1])
    df = df.drop("設定リスト", axis = 1)
    
    return df

def data_reader(df, base, scenario):
    print("Function : ", sys._getframe().f_code.co_name)

    """ # 辞書の定義 """
    dict_prms = {}
    
    for i in range(len(df)):
        key = df.loc[i, "データキーワード"]
        ftype = df.loc[i, "タイプ"]
        file = df.loc[i, "ファイル名"]
        
        print("Read File : ", file)
        
        """ # フォルダ位置の制御 """
        if(ftype == "データ"):
            dir_in = base
        elif(ftype == "パラメータ"):
            dir_in = "./Parameter"
        
        if(key in ["商業地価モデル", "公示地価データ", "地価調査データ"]):
            dict_prms[key] = os.path.join(dir_in, file)
        else:
            if(ftype == "データ" or key in ["遷移確率", "出生率", "転入率", "転出率", "転出総数", "階数割合", "zone重心間800mペア"]):
                icol = None
            else:
                icol = "variable"
            dict_prms[key] = pd.read_csv(os.path.join(dir_in, file), 
                                         encoding = "cp932", index_col = icol)
        
    return dict_prms


def calc_landprice_meanstd(file1_path, file2_path, calctype, root_out):
    """
    入力:
        file1_path (str): 公示地価の.shpファイルのパス。
        file2_path (str): 地価調査の.shpファイルのパス。
        calctype (str) : 住宅地価 or 商業地価
        root_out (str) : 出力パス
        
    出力:
        なし　※平均と標準偏差は root_out に出力する
        
    この関数は、公示地価と地価調査の.shpファイルを読み込み、'店舗' or '住宅' という文字列を含むレコードに絞り、
    平均と標準偏差を計算する
    """
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # キーワード設定 """
    if(calctype == "住宅地価"):
        name = "住宅"
    elif(calctype == "商業地価"):
        name = "店舗"
    else:
        print("calctype keyword is wrong !!")
        print("calctype : 住宅地価 / 商業地価")
        sys.exit(0)
    
    """ # 公示地価の.shpファイルを読み込む """
    gdf1 = gpd.read_file(file1_path)
    
    """ # L01_025列に name で指定した文字が含まれるレコードに絞る """
    gdf1_filtered = gdf1[gdf1['L01_025'].str.contains(name, na=False)]
    
    """ # L01_006, L01_025の2列に絞り、列名を変更する """
    gdf1_filtered = gdf1_filtered[['L01_006', 'L01_025', 'geometry']]
    gdf1_filtered.columns = ['Price', 'Usage', 'geometry']
    # print(gdf1_filtered)
    
    """ # 地価調査についても同様 """
    gdf2 = gpd.read_file(file2_path)
    gdf2_filtered = gdf2[gdf2['L02_025'].str.contains(name, na=False)]
    gdf2_filtered = gdf2_filtered[['L02_006', 'L02_025', 'geometry']]
    gdf2_filtered.columns = ['Price', 'Usage', 'geometry']

    """ # 両者を縦に結合する """
    gdf_combined = gpd.GeoDataFrame(pd.concat([gdf1_filtered, gdf2_filtered], ignore_index=True))
    
    """ # ジオメトリが重複しているレコードを削除する """
    gdf_combined = gdf_combined.drop_duplicates(subset=['geometry'])

    """ # Priceを数値にしておく """
    gdf_combined['Price'] = pd.to_numeric(gdf_combined['Price'], errors='coerce')
    
    """ # Priceの平均と標準偏差を計算 """
    mean_price = gdf_combined['Price'].mean()
    std_price = gdf_combined['Price'].std()
    
    """ # ln(Price)の平均と標準偏差を計算 """
    lnmean_price = np.log(gdf_combined['Price']).mean()
    lnstd_price = np.log(gdf_combined['Price']).std()

    """ # データフレームにして戻す """
    df = pd.DataFrame({'variable': [f"{calctype}", f"ln_{calctype}"],
                       "means":[mean_price, lnmean_price],
                       "stds":[std_price, lnstd_price]
                       })
    # df.to_csv(rf"{root_out}/{calctype}_平均標準偏差.csv", index = False, encoding = "cp932")
    
    df = df.set_index("variable")
    
    return df, gdf_combined


def calc_stdmean(df, targetlist):
    aves = []
    stds = []
    
    for col in targetlist:
        aves.append(df[col].mean())
        stds.append(df[col].std())
    
    df_out = pd.DataFrame({"variable":targetlist,
                           "means":aves,
                           "stds":stds},
                          )
    df_out = df_out.set_index("variable")
    
    return df_out

def calc_minmax(df, targetlist):
    aves = []
    stds = []
    
    for col in targetlist:
        aves.append(df[col].min())
        stds.append(df[col].max())
    
    df_out = pd.DataFrame({"variable":targetlist,
                           "min":aves,
                           "max":stds},
                          )
    df_out = df_out.set_index("variable")
    
    return df_out

def set_stdmean(dfs_dict, df_distfacil, df_individual, year, root_out):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # ACCの標準化 """
    """ # ACCはZoneデータにくっついているので,抜き出しておく """
    df = dfs_dict["Zone"].copy()
    df["ACC_transit_ln"] = np.log(df["ACC_transit"]+1)
    df["ACC_car_ln"] = np.log(df["ACC_car"]+1)
    df["ACC_walk_ln"] = np.log(df["ACC_walk"]+1)
    df["ACC_ln"] = np.log(df["ACC_transit"]+df["ACC_car"]+1)
    
    """ # 対象列は """
    cols = ["ACC_transit", "ACC_car", "ACC_walk", "ACC_transit_ln", "ACC_car_ln", "ACC_walk_ln", "ACC_ln"]    
    dfs_dict["ACC平均標準偏差"] = calc_stdmean(df, cols)
    # dfs_dict["ACC平均標準偏差"].to_csv(rf"{root_out}/ACC平均標準偏差.csv", encoding = "cp932")

    """ # ACCPの標準化 """
    """ # データフレームは同じだけどln ver.を作っておく """
    df["ACCP_transit_ln"] = np.log(df["ACCP_transit"])
    df["ACCP_car_ln"] = np.log(df["ACCP_car"])
    df["ACCP_ln"] = np.log(df["ACCP_transit"]+df["ACCP_car"])

    """ # 対象列は """
    cols = ["ACCP_transit", "ACCP_car", "ACCP_transit_ln", "ACCP_car_ln", "ACCP_ln"]
    dfs_dict["ACCP平均標準偏差"] = calc_stdmean(df, cols)
    # dfs_dict["ACCP平均標準偏差"].to_csv(rf"{root_out}/ACCP平均標準偏差.csv", encoding = "cp932")
    
    """ # 商業地域ダミー """
    df["sgtiki"] = df["UseDistrict"].apply(lambda x:1 if x==10 else 0)
    cols = ["sgtiki"]
    dfs_dict["商業地域ダミー平均標準偏差"] = calc_stdmean(df, cols)
    # dfs_dict["商業地域ダミー平均標準偏差"].to_csv(rf"{root_out}/商業地域ダミー平均標準偏差.csv", encoding = "cp932")

    """ # 容積率 """
    df["ln_floorAreaRate"] = np.log(df["floorAreaRate"])
    cols = ["floorAreaRate", "ln_floorAreaRate"]
    dfs_dict["容積率平均標準偏差"] = calc_stdmean(df, cols)
    # dfs_dict["容積率平均標準偏差"].to_csv(rf"{root_out}/容積率平均標準偏差.csv", encoding = "cp932")

    """ # ゾーン別施設,駅平均距離 """
    """ # 対象列は """
    df["Avg_Dist_sta_centre_ln"] = np.log(df["Avg_Dist_sta_centre"])
    df["Avg_Dist_sta_main_ln"] = np.log(df["Avg_Dist_sta_main"])
    df["Avg_Dist_sta_other_ln"] = np.log(df["Avg_Dist_sta_other"])
    cols = ["Avg_Dist_sta_centre", "Avg_Dist_sta_main", "Avg_Dist_sta_other","Avg_Dist_sta_centre_ln","Avg_Dist_sta_main_ln","Avg_Dist_sta_other_ln"]
    dfs_dict["ゾーン別駅距離平均標準偏差"] = calc_stdmean(df, cols)
    # dfs_dict["ゾーン別駅距離平均標準偏差"].to_csv(rf"{root_out}/ゾーン別駅距離平均標準偏差.csv", encoding = "cp932")
    
    cols = ["Avg_Dist_Zone_to_PreSchool", "Avg_Dist_Zone_to_ElementarySchool",
            "Avg_Dist_Zone_to_Library", "Avg_Dist_Zone_to_MiddleSchool",
            "Avg_Dist_Zone_to_Hospital", "Avg_Dist_Zone_to_Clinic"
            ]
    dfs_dict["ゾーン別施設距離平均標準偏差"] = calc_stdmean(df_distfacil, cols)
    # dfs_dict["ゾーン別施設距離平均標準偏差"].to_csv(rf"{root_out}/ゾーン別施設距離平均標準偏差.csv", encoding = "cp932")
    
    """ # 人口密度(人/ha)の標準化 """
    # year1pb = year - 1
    # """ # ゾーン別人口集計 """
    # df_indagg = df_individual.groupby([f"zone_code{year1pb}"], as_index = False).agg({"Expansion_Factor":"sum"})
    # df_indagg = df_indagg.rename(columns = {f"zone_code{year1pb}":"zone_code", "Expansion_Factor":"zone_pop"})

    """ # 人口密度(人/ha)の標準化 多分こうじゃないかな 2020年スタートなら2020年の人口で計算 """
    """ # ゾーン別人口集計 """
    df_indagg = df_individual.groupby([f"zone_code{year}"], as_index = False).agg({"Expansion_Factor":"sum"})
    df_indagg = df_indagg.rename(columns = {f"zone_code{year}":"zone_code", "Expansion_Factor":"zone_pop"})

    """ # 人口密度を計算する """
    df = pd.merge(df, df_indagg, how = "left", on = ["zone_code"]).fillna(0)
    df["popdens"] = df["zone_pop"] / (df["AREA"] / 10000)

    """ # 標準化 """    
    dfs_dict["人口密度平均標準偏差"] = calc_stdmean(df, ["popdens"])
    # dfs_dict["人口密度平均標準偏差"].to_csv(rf"{root_out}/人口密度平均標準偏差.csv", encoding = "cp932")
    
    
    return dfs_dict

