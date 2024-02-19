#coding:Shift_Jis
import sys
import os
import csv
import numpy as np
import pandas as pd
import geopandas as gpd
import math
import datetime
from shapely.geometry import Point
from sklearn.neighbors import NearestNeighbors
import pyproj
import los_calc
import warnings

def calc_los_rail(indir, outdir, src_proj, dst_proj, df_zn):
    warnings.simplefilter('ignore', FutureWarning)

    #使用ファイルを指定
    path_station = indir + '/Rail_Station.csv' #駅位置
    path_rail_nw = indir + '/Rail_NW.csv' #鉄道NW
    path_rail_fare_dist = indir + '/Rail_Fare_Dist.csv' #運賃テーブル（対距離）
    path_rail_fare_sec = indir + '/Rail_Fare_Table.csv' #運賃テーブル（特定区間）

    if os.path.exists(path_station) != True:
        print('駅コード:' + path_station + 'がありません')
        print('鉄道LOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los
    if os.path.exists(path_rail_nw) != True:
        print('鉄道NW:' + path_rail_nw + 'がありません')
        print('鉄道LOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los
    if os.path.exists(path_rail_fare_dist) != True:
        print('鉄道運賃テーブル（対距離）:' + path_rail_fare_dist + 'がありません')
        print('鉄道LOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los
    if os.path.exists(path_station) != True:
        print('鉄道運賃テーブル（特定区間）:' + path_station + 'がありません')
        print('鉄道LOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los

    print(datetime.datetime.now().time(),'データ読込開始')
    #駅コード読込
    #if os.path.exists(path_station) != True:
    #    print('駅コード:' + path_station + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'駅コード読込：' + path_station)
    dtype_station = {0: str, 1: str, 2: str, 3: str, 4: float, 5: float, 6: str, 7: int}
    df_station = pd.read_csv(path_station, encoding='shift-jis',dtype=dtype_station) 
    col_station_name = df_station.columns.values
    lst_station = list(df_station.iloc[:, 0])


    #鉄道NWデータ読込
    #if os.path.exists(path_rail_nw) != True:
    #    print('鉄道NW:' + path_rail_nw + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'鉄道NW読込：' + path_rail_nw)
    dtype_rail_nw = {0: str, 1: str, 2: str, 3: int, 4: int, 5: float, 6: float, 7: float, 8: float, 9: float, 10: float}
    df_rail_nw_tmp = pd.read_csv(path_rail_nw, encoding='shift-jis',dtype=dtype_rail_nw) 
    col_name_rail = df_rail_nw_tmp.columns.values


    #鉄道NWデータの補完
    fill_values = {col_name_rail[5]: 0.0, col_name_rail[6]: 0.0, col_name_rail[7]: 0.0, col_name_rail[8]: 0.0, col_name_rail[9]: 0.0, col_name_rail[10]: 0.0}
    df_rail_nw_tmp = df_rail_nw_tmp.fillna(fill_values)
    df_rail_nw_tmp = df_rail_nw_tmp.copy()


    #鉄道運賃テーブル（対距離）の読込
    #if os.path.exists(path_rail_fare_dist) != True:
    #    print('鉄道運賃テーブル（対距離）:' + path_rail_fare_dist + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'鉄道運賃テーブル（対距離）読込：' + path_rail_fare_dist)
    dtype_rail_fare_dist = {0: str, 1: int, 2: int, 3: float, 4: str}
    df_rail_fare_dist = pd.read_csv(path_rail_fare_dist, encoding='shift-jis',dtype=dtype_rail_fare_dist) 


    #鉄道運賃テーブル（特定区間）の読込
    #if os.path.exists(path_station) != True:
    #    print('鉄道運賃テーブル（特定区間）:' + path_station + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'鉄道運賃テーブル（特定区間）読込：' + path_station)
    dtype_rail_fare_sec = {0: str, 1: str, 2: float, 3: str, 4: str}
    df_rail_fare_sec = pd.read_csv(path_rail_fare_sec, encoding='shift-jis',dtype=dtype_rail_fare_sec) 
    df_rail_fare_sec['ID'] = df_rail_fare_sec.iloc[:, 0] + df_rail_fare_sec.iloc[:, 1]

    print(datetime.datetime.now().time(),'データ読込終了')
    print(datetime.datetime.now().time(),'鉄道LOS計算開始')


    #路線リストの作成
    lst_line = list(set(df_station.iloc[:, 1] + df_station.iloc[:, 2]))
    lst_line.sort()

    df_rail_nw = pd.DataFrame(columns=col_name_rail) #路線別に駅間総当たりのNWのための空のデータフレーム
    nlink = 0
    #路線別に経路探索 駅間の平均所要時間と運行本数を算出
    for line in lst_line:
        #距離の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy() #路線別に抽出
        df_rail_line = df_rail_line.reset_index(drop=True) #インデックスが引き継がれるので振り直し

        #ノードSEQの作成
        #駅ダミーノード
        nam_rail_line_0 = list(set(pd.concat([df_rail_line[df_rail_line[col_name_rail[1]].str[-1] == '0'].iloc[:, 1], df_rail_line[df_rail_line[col_name_rail[2]].str[-1] == '0'].iloc[:, 2]])))
        nam_rail_line_0.sort()
        #駅ノード
        nam_rail_line_1 = list(set(pd.concat([df_rail_line[df_rail_line[col_name_rail[1]].str[-1] != '0'].iloc[:, 1], df_rail_line[df_rail_line[col_name_rail[2]].str[-1] != '0'].iloc[:, 2]])))
        nam_rail_line_1.sort()
        #ノードリスト
        nam_rail_line = nam_rail_line_0 + nam_rail_line_1
        nam_rail_line

        lf = []
        for i in df_rail_line.iloc[:, 1]:
            lf.append(nam_rail_line.index(i))
        df_rail_line['FromノードSEQ'] = lf

        lt = []
        for i in df_rail_line.iloc[:, 2]:
            lt.append(nam_rail_line.index(i))
        df_rail_line['ToノードSEQ'] = lt
        col_name_rail_line = df_rail_line.columns.values

        #リンク接続情報をforward star形式に変換
        #初期化
        jla = [0] * (len(nam_rail_line) + 1)
        jlx = [0] * (len(df_rail_line) * 2)
        lij = [0] * len(df_rail_line)
        los_calc.forwardstar(len(df_rail_line), len(nam_rail_line), list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), jla, jlx, lij)

        #営業キロ
        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 5]
        lvm = df_rail_line.iloc[:, 5]

        #経路探索
        dist_line1 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))

        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            dist_line1[iz] = minv[:len(nam_rail_line_0)]

        #換算キロ
        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 6]
        lvm = df_rail_line.iloc[:, 6]

        #経路探索
        dist_line2 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))

        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            dist_line2[iz] = minv[:len(nam_rail_line_0)]
        
        
        hv = 99990.0 #経路探索のためのhigh value
        #各駅列車乗車（急行幹線リンクなし）の探索
        #From→To側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #急行リンクにハイバリュー
        df_rail_line.loc[df_rail_line[col_name_rail[4]] == 2,  col_name_rail[7]] = hv
        df_rail_line.loc[df_rail_line[col_name_rail[4]] == 2,  col_name_rail[8]] = hv
        #各駅幹線リンクのTo→Fromにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[8]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line11 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line11 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line11 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line11[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 9]))
                if hon != 999: railtype_line11[iz, jz] = railtype
                if hon != 999: hon_line11[iz, jz] = hon

        tim_line11 = np.where(tim_line11 >= hv / 10, 0, tim_line11)
        tim_line11 = np.where(tim_line11 == 0, 0, tim_line11 - 2) #駅ダミーリンクの所要時間を除く

        #To→From側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #急行リンクにハイバリュー
        df_rail_line.loc[df_rail_line[col_name_rail[4]] == 2,  col_name_rail[7]] = hv
        df_rail_line.loc[df_rail_line[col_name_rail[4]] == 2,  col_name_rail[8]] = hv
        #各駅幹線リンクのFrom→Toにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[7]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line12 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line12 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line12 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line12[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 10]))
                if hon != 999: railtype_line12[iz, jz] = railtype
                if hon != 999: hon_line12[iz, jz] = hon

        tim_line12 = np.where(tim_line12 >= hv / 10, 0, tim_line12)
        tim_line12 = np.where(tim_line12 == 0, 0, tim_line12 - 2)

        tim_line1 = tim_line11 + tim_line12
        railtype_line1 = railtype_line11 + railtype_line12
        hon_line1 = hon_line11 + hon_line12


        #各駅列車乗車（急行幹線リンクあり）の探索
        #From→To側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #急行駅ダミーリンクの乗車側にハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 2) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[7]] = hv
        #各駅幹線リンクのTo→Fromにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[8]] = hv
        #急行幹線リンクのTo→Fromにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[8]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line21 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line21 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line21 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line21[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 9]))
                if hon != 999: railtype_line21[iz, jz] = railtype
                if hon != 999: hon_line21[iz, jz] = hon
                if railtype == 1: #急行なしと同じ結果
                    hon_line21[iz, jz] = 0
                    tim_line21[iz, jz] = 0

        tim_line21 = np.where(tim_line21 >= hv / 10, 0, tim_line21)
        tim_line21 = np.where(tim_line21 == 0, 0, tim_line21 - 2) #駅ダミーリンクの所要時間を除く

        #To→From側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #急行駅ダミーリンクの乗車側にハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 2) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[7]] = hv
        #各駅幹線リンクのFrom→Toにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[7]] = hv
        #急行幹線リンクのFrom→Toにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[7]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line22 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line22 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line22 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line22[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 10]))
                if hon != 999: railtype_line22[iz, jz] = railtype
                if hon != 999: hon_line22[iz, jz] = hon
                if railtype == 1: #急行なしと同じ結果
                    hon_line22[iz, jz] = 0
                    tim_line22[iz, jz] = 0

        tim_line22 = np.where(tim_line22 >= hv / 10, 0, tim_line22)
        tim_line22 = np.where(tim_line22 == 0, 0, tim_line22 - 2)

        tim_line2 = tim_line21 + tim_line22
        railtype_line2 = railtype_line21 + railtype_line22
        hon_line2 = hon_line21 + hon_line22


        #急行列車乗車の探索
        #From→To側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #各駅駅ダミーリンクの乗車側にハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 2) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[7]] = hv
        #各駅幹線リンクのTo→Fromにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[8]] = hv
        #急行幹線リンクのTo→Fromにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[8]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line31 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line31 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line31 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line31[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 9]))
                if hon != 999: railtype_line31[iz, jz] = railtype
                if hon != 999: hon_line31[iz, jz] = hon

        tim_line31 = np.where(tim_line31 >= hv / 10, 0, tim_line31)
        tim_line31 = np.where(tim_line31 == 0, 0, tim_line31 - 2) #駅ダミーリンクの所要時間を除く

        #To→From側の探索
        #探索NWの設定
        df_rail_line = df_rail_nw_tmp[(df_rail_nw_tmp[col_name_rail[1]].str[:len(line)] == line) & (df_rail_nw_tmp[col_name_rail[3]] <= 3)].copy()
        df_rail_line = df_rail_line.reset_index(drop=True)

        #各駅駅ダミーリンクの乗車側にハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 2) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[7]] = hv
        #各駅幹線リンクのFrom→Toにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 1),  col_name_rail[7]] = hv
        #急行幹線リンクのFrom→Toにハイバリュー
        df_rail_line.loc[(df_rail_line[col_name_rail[3]] == 1) & (df_rail_line[col_name_rail[4]] == 2),  col_name_rail[7]] = hv

        #ノードSEQをセット
        df_rail_line['FromノードSEQ'] = lf
        df_rail_line['ToノードSEQ'] = lt

        #リンクコストの設定
        lvp = df_rail_line.iloc[:, 7] / 10.0
        lvm = df_rail_line.iloc[:, 8] / 10.0

        #経路探索
        tim_line32 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        railtype_line32 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        hon_line32 = np.zeros((len(nam_rail_line_0), len(nam_rail_line_0)))
        for iz in range(len(nam_rail_line_0)):
            ndin = iz #探索起点
            minv = [math.inf] * len(nam_rail_line)
            nxt = [-1] * len(nam_rail_line)
            lno = [0] * len(nam_rail_line)

            #ダイクストラ法による最短経路探索
            los_calc.dijkstra_rail_line(ndin, len(nam_rail_line), minv, list(df_rail_line.iloc[:, 11]), list(df_rail_line.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_line.iloc[:, 3]))
            tim_line32[iz] = minv[:len(nam_rail_line_0)]

            #経路探索結果から運行本数を計算
            for jz in range(len(nam_rail_line_0)):
                if iz == jz: continue
                if minv[jz] >= hv / 10: continue
                ndtb = []
                lktb = []
                ierr, ir, railtype, hon = los_calc.rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, list(df_rail_line.iloc[:, 3]), list(df_rail_line.iloc[:, 4]), list(df_rail_line.iloc[:, 10]))
                if hon != 999: railtype_line32[iz, jz] = railtype
                if hon != 999: hon_line32[iz, jz] = hon

        tim_line32 = np.where(tim_line32 >= hv / 10, 0, tim_line32)
        tim_line32 = np.where(tim_line32 == 0, 0, tim_line32 - 2)

        tim_line3 = tim_line31 + tim_line32
        railtype_line3 = railtype_line31 + railtype_line32
        hon_line3 = hon_line31 + hon_line32

        #各探索結果から運行本数を計算
        hon_line = np.maximum(hon_line1, hon_line2) + hon_line3

        #各探索結果から所要時間を計算 運行本数データなしに対応（運行本数1本として計算）
        np_dmy = np.ones((len(nam_rail_line_0), len(nam_rail_line_0)))
        sumtim = tim_line1 * np.maximum(hon_line1, np_dmy) + tim_line2 * np.maximum(hon_line2, np_dmy) + tim_line3 * np.maximum(hon_line3, np_dmy)
        hon_line1 = np.maximum(hon_line1, np.divide(tim_line1, tim_line1, out=np.zeros_like(tim_line1, dtype=np.float64), where=tim_line1 != 0))
        hon_line2 = np.maximum(hon_line2, np.divide(tim_line2, tim_line2, out=np.zeros_like(tim_line2, dtype=np.float64), where=tim_line2 != 0))
        hon_line3 = np.maximum(hon_line3, np.divide(tim_line3, tim_line3, out=np.zeros_like(tim_line3, dtype=np.float64), where=tim_line3 != 0))
        sumhon = hon_line1 + hon_line2 + hon_line3

        tim_line = np.divide(sumtim, sumhon, out=np.zeros_like(sumtim, dtype=np.float64), where=sumhon != 0)

        lst_dmy = []
        for i in range(len(nam_rail_line_0)):
            for j in range(len(nam_rail_line_0)):
                if i < j:
                    nlink += 1
                    lst_dmy.append([str(nlink), nam_rail_line_0[i], nam_rail_line_0[j], 1, 1, round(dist_line1[i, j], 1), round(dist_line2[i, j], 1), tim_line[i, j], tim_line[j, i], hon_line[i, j], hon_line[j, i]])
        df_rail_nw_dmy = pd.DataFrame(lst_dmy, columns=col_name_rail)
        df_rail_nw = pd.concat([df_rail_nw, df_rail_nw_dmy], axis=0, ignore_index=True)
    
    df_rail_nw_dmy = df_rail_nw_tmp[df_rail_nw_tmp[col_name_rail[3]] == 4].copy() #乗換リンクに抽出
    df_rail_nw_dmy.iloc[:,7] = df_rail_nw_dmy.iloc[:,7] / 10
    df_rail_nw_dmy.iloc[:,8] = df_rail_nw_dmy.iloc[:,8] / 10
    df_rail_nw = pd.concat([df_rail_nw, df_rail_nw_dmy], axis=0, ignore_index=True)
    df_rail_nw.iloc[:,1] = df_rail_nw.iloc[:,1].str[:len(lst_station[0])]
    df_rail_nw.iloc[:,2] = df_rail_nw.iloc[:,2].str[:len(lst_station[0])]


    #ノードSEQをセット
    lf = []
    for i in df_rail_nw.iloc[:, 1]:
        lf.append(lst_station.index(i))
    df_rail_nw['FromノードSEQ'] = lf

    lt = []
    for i in df_rail_nw.iloc[:, 2]:
        lt.append(lst_station.index(i))
    df_rail_nw['ToノードSEQ'] = lt
    col_name_rail_nw = df_rail_nw.columns.values

    #リンク接続情報をforward star形式に変換
    #初期化
    jla = [0] * (len(lst_station) + 1)
    jlx = [0] * (len(df_rail_nw) * 2)
    lij = [0] * len(df_rail_nw)
    los_calc.forwardstar(len(df_rail_nw), len(lst_station), list(df_rail_nw.iloc[:, 11]), list(df_rail_nw.iloc[:, 12]), jla, jlx, lij)

    #リンクコストの設定
    #乗車時間
    lvp = df_rail_nw.iloc[:, 7].copy()
    lvm = df_rail_nw.iloc[:, 8].copy()
    #待ち時間を加算
    lvp += np.divide(30.0, df_rail_nw.iloc[:, 9], out=np.zeros_like(df_rail_nw.iloc[:, 9], dtype=np.float64), where=(df_rail_nw.iloc[:, 3] == 1) & (df_rail_nw.iloc[:, 9] != 0))
    lvm += np.divide(30.0, df_rail_nw.iloc[:, 10], out=np.zeros_like(df_rail_nw.iloc[:, 10], dtype=np.float64), where=(df_rail_nw.iloc[:, 3] == 1) & (df_rail_nw.iloc[:, 10] != 0))


    #経路探索
    tim_rail = np.zeros((len(lst_station), len(lst_station)))
    tim_rail_wait = np.zeros((len(lst_station), len(lst_station)))
    fare_rail = np.zeros((len(lst_station), len(lst_station)))
    len_agency = len(df_station.iloc[0, 1])

    for iz in range(len(lst_station)):
        ndin = iz #探索起点
        minv = [math.inf] * len(lst_station)
        nxt = [-1] * len(lst_station)
        lno = [0] * len(lst_station)

        #ダイクストラ法による最短経路探索
        los_calc.dijkstra_rail(ndin, len(lst_station), minv, list(df_rail_nw.iloc[:, 11]), list(df_rail_nw.iloc[:, 12]), lvp, lvm, jla, jlx, nxt, lno, list(df_rail_nw.iloc[:, 3]))
    
        #経路探索結果から所要時間（幹線時間と待ち時間）と運賃を計算
        for jz in range(len(lst_station)):
            if iz == jz: continue
            ndtb = []
            lktb = []
            ierr, ir, tim_rail[iz, jz], tim_rail_wait[iz, jz], fare_rail[iz, jz] = los_calc.rotout_rail(iz, jz, nxt, lno, ndtb, lktb, lst_station, len_agency, df_rail_nw, df_rail_fare_dist, df_rail_fare_sec)


    #駅アクセス算出
    znsta = [] #ゾーン別アクセス駅のリスト
    dist_znsta = [] #ゾーン別アクセス駅への距離リスト
    transformer = pyproj.Transformer.from_crs(src_proj, dst_proj)
    #座標変換
    sta_x, sta_y = transformer.transform(df_station.iloc[:, 4], df_station.iloc[:, 5])
    zn_x, zn_y = transformer.transform(df_zn.iloc[:, 1], df_zn.iloc[:, 2])
    #ノードの位置関係を学習
    sta_xy_array = np.array([sta_x, sta_y]).T
    knn_num = len(df_station) #探索ノード数
    knn_model = NearestNeighbors(n_neighbors = knn_num, algorithm = 'ball_tree').fit(sta_xy_array)

    for zn in range(len(df_zn)):
        zn_xy = [zn_x[zn], zn_y[zn]]
        knn_dists, knn_results = knn_model.kneighbors([zn_xy])

        lst_sta = []
        lst_dist = []

        #最大10kmまで1km単位で範囲を広げて、アクセスする駅を特定
        maxdist = math.ceil(knn_dists[:,0][0] / 1000) #最寄り駅
        if maxdist > 10:
            pass
        else:
            for ix in range(knn_num):
                if knn_dists[:,ix][0] / 1000 > maxdist:
                    break
                else:
                    lst_sta.append(knn_results[:,ix][0])
                    lst_dist.append(knn_dists[:,ix][0])
        znsta.append(lst_sta)
        dist_znsta.append(lst_dist)


    #ゾーン間LOSを計算
    #出力用のデータフレームを準備
    df_los = pd.DataFrame(columns=['zone_code_o', 'zone_code_d', 'Travel_Time_Rail', 'Waiting_Time_Rail', 'Access_Time_Rail', 'Egress_Time_Rail', 'Fare_Rail'])
    lst_jz = df_zn.iloc[:, 0]

    for iz in range(len(df_zn)):
        lst_los = []
        for jz in range(len(df_zn)):
            sumtim = 9999.0
            min_i = len(df_station)
            min_j = len(df_station)
            if iz == jz:
                lst_los.append([0,0,0,0,0,0,0])
            else:
                for i, sta_acs in enumerate(znsta[iz]):
                    for j, sta_egr in enumerate(znsta[jz]):
                        if sta_acs == sta_egr: continue
                        if sumtim > tim_rail[sta_acs, sta_egr] + tim_rail_wait[sta_acs, sta_egr] + \
                                    dist_znsta[iz][i] * math.sqrt(2) / 80.0 + \
                                    dist_znsta[jz][j] * math.sqrt(2) / 80.0:
                            sumtim = tim_rail[sta_acs, sta_egr] + tim_rail_wait[sta_acs, sta_egr] + \
                                    dist_znsta[iz][i] * math.sqrt(2) / 80.0 + \
                                    dist_znsta[jz][j] * math.sqrt(2) / 80.0
                            min_i = i
                            min_j = j
                if sumtim == 9999.0:
                    lst_los.append([0,0,9999.0,9999.0,9999.0,9999.0,9999.0])
                else:
                    lst_los.append([0,0,tim_rail[znsta[iz][min_i],znsta[jz][min_j]],tim_rail_wait[znsta[iz][min_i], znsta[jz][min_j]],round(dist_znsta[iz][min_i] * math.sqrt(2) / 80.0, 1),round(dist_znsta[jz][min_j] * math.sqrt(2) / 80.0, 1),fare_rail[znsta[iz][min_i], znsta[jz][min_j]]])

        df_los_zn = pd.DataFrame(lst_los, columns=['zone_code_o', 'zone_code_d', 'Travel_Time_Rail', 'Waiting_Time_Rail', 'Access_Time_Rail', 'Egress_Time_Rail', 'Fare_Rail'])
        df_los_zn.iloc[:, 0] = lst_jz[iz]
        df_los_zn.iloc[:, 1] = lst_jz
        df_los = pd.concat([df_los, df_los_zn], axis=0, ignore_index=True)

    print(datetime.datetime.now().time(),'鉄道LOS計算終了')
    return df_los


def los_dmy(df_zn):
    df_los = pd.DataFrame(columns=['zone_code_o', 'zone_code_d', 'Travel_Time_Rail', 'Waiting_Time_Rail', 'Access_Time_Rail', 'Egress_Time_Rail', 'Fare_Rail'])
    lst_jz = df_zn.iloc[:, 0]
    
    for iz in range(len(df_zn)):
        lst_los = []
        for jz in range(len(df_zn)):
            if iz == jz:
                lst_los.append([0,0,0,0,0,0,0])
            else:
                lst_los.append([0,0,9999.0,9999.0,9999.0,9999.0,9999.0])

        df_los_zn = pd.DataFrame(lst_los, columns=['zone_code_o', 'zone_code_d', 'Travel_Time_Rail', 'Waiting_Time_Rail', 'Access_Time_Rail', 'Egress_Time_Rail', 'Fare_Rail'])
        df_los_zn.iloc[:, 0] = lst_jz[iz]
        df_los_zn.iloc[:, 1] = lst_jz
        df_los = pd.concat([df_los, df_los_zn], axis=0, ignore_index=True)
    return df_los
