# -*- coding: utf-8 -*-

import os
import sys

import numpy as np
import pandas as pd


def agg_buildings(df, year):
    
    df = df.copy()

    """ # ダミー変数(足しこむ用) """
    df["建物数"] = 1
    
    """ # ゾーン別用途別に集計 """
    df_p = pd.pivot_table(df, values = "建物数", index = "zone", columns = f"yoto{year}", aggfunc = sum)
    
    """ # 適当に0埋めして """
    df_p = df_p.fillna(0)
    
    """ # indexを戻して """
    df_p = df_p.reset_index()
    
    """ # 建物数の合計を作る """
    """ # .sum(axis = 1)で空地分も足されるので、空地だけ引く """
    df_p["建物数_合計"] = df_p.sum(axis = 1, numeric_only = True) - df_p["空地"]
    
    """ # 並び替える """
    df_p = df_p[["zone", "建物数_合計", "住宅", "共同住宅", "商業施設", "店舗等併用住宅", "店舗等併用共同住宅", "空地"]]
    
    """ # 列名変更用の辞書 """
    dic_col = {}
    for col in df_p.columns.values:
        if(col == "zone"):
            dic_col["zone"] = "zone_code"
        elif(col != "建物数_合計"):
            dic_col[col] = f"建物数_{col}"
    
    """ # リネーム """
    df_p = df_p.rename(columns = dic_col)
    
    return df_p

def agg_areas(df, year):
    """ # ゾーン別用途別に集計 """
    df_p = pd.pivot_table(df[df[f"existing{year}"] == 1], values = f"floorarea{year}", index = "zone", columns = f"yoto{year}", aggfunc = sum)

    """ # 「0」埋めしておく """
    df_p = df_p.fillna(0)
    
    """ # reset_index でindexを直しておく """
    df_p = df_p.reset_index()

    """ # 延べ床面積の合計を作っておいて """
    df_p["延床面積_合計"] = df_p.sum(axis = 1, numeric_only = True)

    """ # 並び替える """
    df_p = df_p[["zone", "延床面積_合計", "住宅", "共同住宅", "商業施設", "店舗等併用住宅", "店舗等併用共同住宅"]]

    """ # 列名変更用の辞書 """
    dic_col = {}
    for col in df_p.columns.values:
        if(col == "zone"):
            dic_col["zone"] = "zone_code"
        elif(col != "延床面積_合計"):
            dic_col[col] = f"延床面積_{col}"
    
    """ # リネーム """
    df_p = df_p.rename(columns = dic_col)

    return df_p

def agg_lgsm(df, year):
    
    """ # ゾーン別に用途選択ログサムの平均値を計算 """
    df_agg = df.groupby(["zone"], as_index = False).agg({f"用途選択モデルログサム変数{year}":"mean"})
    df_agg = df_agg.rename(columns = {"zone":"zone_code"})
    
    return df_agg

def agg_area_pop_build(df_out, area, word):
    """ # 使う列名のリスト """
    cols = ["zone_code", "建物数_合計", "建物数_住宅", "建物数_共同住宅", "建物数_商業施設", 
            "建物数_店舗等併用住宅", "建物数_店舗等併用共同住宅", "建物数_空地", "総人口"]
    
    """ # コピーしておく """
    df_data = df_out[cols].copy()
    
    """ # 圏域フラグのdzone側に人口と建物数をマージする """
    area = pd.merge(area, df_data, how = "left", left_on = ["dzone"], right_on = ["zone_code"])
    
    """ # これで、ozone側で集計すればいい """
    """ # zone_codeが要らないので落としておく """
    cols.pop(0)

    """ # 集計用に辞書を作る """
    agg_dict = dict.fromkeys(cols, "sum")
    
    """ # 集計 """
    area_agg = area[area["flg"] == 1].groupby(["zone_code"], as_index = False).agg(agg_dict)
    
    """ # 列名の変更 """
    dict_rename = {col : word + "_" + col for col in cols}
    area_agg = area_agg.rename(columns = dict_rename)
    
    """ # zone_codeでマージして返す """
    df_out = pd.merge(df_out, area_agg, how = "left", on = ["zone_code"])
    
    return df_out
    
def agg_vacant_rate(df, year):
    
    """ # コピーして使う """
    df = df.copy()
    
    """ # ダミーを追加 """
    df["空家数"] = 1
    
    """ # ゾーン別空家数の集計 """
    df_agg = df[df[f"空家フラグ{year}"] == 1].groupby(["zone"], as_index = False).agg({"空家数":"sum"})
    df_agg = df_agg.rename(columns = {"zone":"zone_code"})
    
    return df_agg


def post_zonedata(dfs_dict, year, start, out_bnum, out_zone):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # まずは出力用のデータフレームを作る """
    df_out = pd.DataFrame()
    
    """ # ゾーンコード一覧をコピー """
    df_out = dfs_dict["ゾーンデータ"].copy()
    
    """ # 面積データをマージ """
    df_out = pd.merge(df_out, dfs_dict["ゾーン別面積"], how = "left", on = ["zone_code"])
    
    """ # 建物数の集計 """
    df_p = agg_buildings(dfs_dict["建物データ"], year)
    
    """ # 出力指定があれば出力 """
    if(out_bnum["設定値"] == "T"):
        df_p.to_csv(rf"{out_bnum['フォルダ名']}/年次別建物数集計_{year}.csv", encoding = "cp932", index = False)

    """ # ゾーンでマージする """
    df_out = pd.merge(df_out, df_p, how = "left", on = ["zone_code"])
    
    """ # 差分作成 """
    """ # まずは入力時の集計 """
    df_pi = agg_buildings(dfs_dict["建物データ_入力値"], start)

    """ # マージして """
    df_pi = pd.merge(df_pi, df_p, how = "outer", on = ["zone_code"], suffixes = ("_入力値", f"_{year}時点"))
    diff_col = ["建物数_合計", "建物数_住宅", "建物数_共同住宅", "建物数_商業施設", "建物数_店舗等併用住宅", "建物数_店舗等併用共同住宅"]
    col_save = ["zone_code"]
    """ # 差分の計算 """
    for col in diff_col:
        col_name = col.split("_")[1]
        df_pi[f"建物数差分_{col_name}"] = df_pi[f"{col}_入力値"] - df_pi[f"{col}_{year}時点"]
        col_save.append(f"建物数差分_{col_name}")
    
    """ # キーとなるゾーンコードと、差分列だけ残して """
    df_pi = df_pi[col_save]
    
    """ # マージする """
    df_out = pd.merge(df_out, df_pi, how = "left", on = ["zone_code"])
    
    """ # 延べ床面積の集計 """
    df_areas = agg_areas(dfs_dict["建物データ"], year)
    
    """ # マージする """
    df_out = pd.merge(df_out, df_areas, how = "left", on = ["zone_code"])
    
    """ # 地価系 """
    """ # 商業地価をマージ """
    df_out = pd.merge(df_out, dfs_dict["商業地価"], how = "left", on = ["zone_code"])
    
    """ # 住宅地価をマージ """
    df_out = pd.merge(df_out, dfs_dict["住宅地価"], how = "left", on = ["zone_code"])
    
    """ # 付け値地代をマージ """
    df_brm = dfs_dict["付け値地代"].copy()
    df_brm = df_brm[["zone_code", "lgsm"]]
    df_out = pd.merge(df_out, df_brm, how = "left", on = ["zone_code"])
    """ # 現状だと単身世帯用の、ログサムしか返してないっぽい… → ちょっと確認するけどひとまずつけておく """
    df_out = df_out.rename(columns = {"lgsm":"付け値地代lgsm_単身世帯"})
    df_out["付け値地代lgsm_夫婦世帯"] = 0.0
    df_out["付け値地代lgsm_そのほか世帯"] = 0.0
    
    """ # 総人口 """
    df_out = pd.merge(df_out, dfs_dict["ゾーン別人口"], how = "left", on = ["zone_code"])
    df_out = df_out.rename(columns = {"pop_all":"総人口"})
    
    """ # 用途選択ログサム変数 """
    """ # ゾーン別の用途選択ログサムの平均値 を入れる """
    df_lgsm = agg_lgsm(dfs_dict["用途選択ログサム"], year)
    df_out = pd.merge(df_out, df_lgsm, how = "left", on = ["zone_code"])
    
    """ # 空家率 """
    df_vbr = agg_vacant_rate(dfs_dict["建物データ"], year)

    """ # zone_codeでマージすればよい """
    df_out = pd.merge(df_out, df_vbr, how = "left", on = ["zone_code"])
    
    """ # 一旦適当に0埋めしてから """
    df_out["空家数"] = df_out["空家数"].fillna(0)
    
    """ # 空家率を計算する """
    df_out["空家率"] = df_out["空家数"] / (df_out["建物数_住宅"] + df_out["建物数_店舗等併用住宅"])
    
    """ # 自動車5分圏内人口・建物数更新 """
    df_out = agg_area_pop_build(df_out, dfs_dict["自動車到達可能圏域"], "自動車5分圏域")
    
    """ # 公共交通20分圏内人口・建物数更新 """
    df_out = agg_area_pop_build(df_out, dfs_dict["公共交通到達可能圏域(20分)"], "公共交通20分圏域")
    
    """ # 公共交通40分圏内人口・建物数更新 """
    df_out = agg_area_pop_build(df_out, dfs_dict["公共交通到達可能圏域(40分)"], "公共交通40分圏域")
        
    
    """ # 出力設定 """
    if(out_zone["設定値"] == "T"):
        df_out = df_out.rename(columns={"付け値地代lgsm_単身世帯":"付け値地代ログサム変数"})
        df_out = df_out.drop(["j_senyo","j_tiki","s_tiki",f"用途選択モデルログサム変数{year}","付け値地代lgsm_夫婦世帯","付け値地代lgsm_そのほか世帯"], axis=1)
        df_out.to_csv(rf"{out_zone['フォルダ名']}/annual_zone_data_{year}.csv", index = False, encoding = "cp932")



def exist_flag(exist, kaitai):
    if(kaitai == -1):
        return exist
    else:
        return 2


def post_output(df, df_status, year, period, col_inp, add_flag, add_data, out_data):
    print("Function : ", sys._getframe().f_code.co_name)
    
    """ # この段階で要らない列は落とす """
    df = df.drop([f"除却判定用乱数{year}", f"建て替え判定用乱数{year}", f"除却フラグ{year}", f"建設有無フラグ{year}"], axis = 1)
    
    """ # 残すのは年次の付かない列名 """
    col_save = col_inp.copy()
    
    """ # このほかに残すのは対象年次が末尾についたもの """
    for col in df.columns.values:
        if(f"{year}" in col):
            col_save.append(col)

    """ # 必要な列を残して """
    df = df[col_save]
    
    """ # 変遷データをマージする """
    df_tmp = df_status[["tatemono_code", "変遷フラグ"]]
    df = pd.merge(df, df_tmp, how = "left", on = ["tatemono_code"])
    
    """ # 年次別データとして出力 """
    """ # 2023/02/07 OSS用に調整 """
    """ # 推計対象外建物の追加結合は内部指定済 """
    """ # ファイル出力のみの選択とする """
    df_res = df.copy()
    df_res = df_res.rename(columns = {f"yoto{year}":"yoto", 
                                      f"existing{year}":"existing",
                                      f"building_age{year}":"building_age",
                                      f"storey{year}":"storey", 
                                      f"area_residence{year}":"area_residence",
                                      f"area_commercial{year}":"area_commercial",
                                      f"floorarea{year}":"floorarea", 
                                      f"display_high_median{year}":"display_high_median" ,
                                      f"空家フラグ{year}":"空家フラグ"
                                      })

    add_data["変遷フラグ"] = "推計対象外"
    add_data["空家フラグ"] = "推計対象外"
    add_data["existing"] = pd.Series(np.vectorize(exist_flag)(add_data["existing"], add_data["kaitai_year"]))
    df_res = pd.concat([df_res, add_data], axis = 0) # 縦結合
    
    if(out_data["設定値"] == "T"):
        df_out = df_res.drop(["usage_code","usage_group",f"用途選択モデルログサム変数{year}"], axis=1)
        df_out.to_csv(rf"{out_data['フォルダ名']}/annual_building_data_{year}.csv", index = False, encoding = "cp932")


    """ # 整理したのでこれを次年度インプットとして返す """
    """ # cityGML用に結合済データも返すように設定変更 """
    return df, df_res
    
