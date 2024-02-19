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

def calc_los_bus(indir, outdir, src_proj, dst_proj, df_zn):
    warnings.simplefilter('ignore', FutureWarning)

    #使用ファイルを指定
    tim_limit = 15.0 #待ち時間の上限
    tim_load = 15.0 #乗換負荷
    tim_ope = 15.0 #運行時間
    tim_wait = 3.0 #初乗り待ち時間（時刻表に合わせてバス停に行くので運行本数とは関係なく設定）

    #使用ファイルを指定
    path_bus_stop = indir + '/Bus_Stop.csv' #バス位置
    path_bus_nw = indir + '/Bus_NW.csv' #バスNW
    path_bus_fare = indir + '/Bus_Fare.csv' #運賃テーブル
    path_shp_zn = indir + '/Zone_Polygon.shp' #ゾーンのshp


    if os.path.exists(path_bus_stop) != True:
        print('バス停コード:' + path_bus_stop + 'がありません')
        print('バスLOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los
    if os.path.exists(path_bus_nw) != True:
        print('バスNW:' + path_bus_nw + 'がありません')
        print('バスLOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los
    if os.path.exists(path_bus_fare) != True:
        print('バス運賃テーブル:' + path_bus_fare + 'がありません')
        print('バスLOS作成をスキップします')
        df_los = los_dmy(df_zn)
        return df_los


    print(datetime.datetime.now().time(),'データ読込開始')
    #バス停コード読込
    #if os.path.exists(path_bus_stop) != True:
    #    print('バス停コード:' + path_bus_stop + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'バス停コード読込：' + path_bus_stop)
    dtype_bus_stop = {0: str, 1: str, 2: float, 3: float, 4: str}
    df_bus_stop = pd.read_csv(path_bus_stop, encoding='shift-jis',dtype=dtype_bus_stop) 
    col_bus_stop_name = df_bus_stop.columns.values
    df_bus_stop['id'] = df_bus_stop['agency_id'] + '_' + df_bus_stop['stop_id']
    df_bus_stop = df_bus_stop.sort_values('id').reset_index(drop=True)
    lst_bus_stop = list(df_bus_stop .iloc[:, -1])


    #バスNWデータ読込
    #if os.path.exists(path_bus_nw) != True:
    #    print('バスNW:' + path_bus_nw + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'バスNW読込：' + path_bus_nw)
    dtype_bus_nw = {0: str, 1: str, 2: str, 3: str, 4: str, 5: float, 6: float}
    df_bus_nw_tmp = pd.read_csv(path_bus_nw, encoding='shift-jis',dtype=dtype_bus_nw) 
    col_name_bus = df_bus_nw_tmp.columns.values

    #バスNWデータの補完
    fill_values = {col_name_bus[5]: 0.0, col_name_bus[6]: 0.0}
    df_bus_nw_tmp = df_bus_nw_tmp.fillna(fill_values)
    df_bus_nw_tmp = df_bus_nw_tmp.copy()


    #バス運賃テーブルの読込
    #if os.path.exists(path_bus_fare) != True:
    #    print('バス運賃テーブル:' + path_bus_fare + 'がありません')
    #    os.system('PAUSE')
    #    sys.exit()
    print(datetime.datetime.now().time(),'バス運賃テーブル読込：' + path_bus_fare)
    dtype_bus_fare = {0: str, 1: str, 2: str, 3: str, 4: float}
    df_bus_fare_tmp = pd.read_csv(path_bus_fare, encoding='shift-jis',dtype=dtype_bus_fare) 
    df_bus_fare_tmp['id'] = df_bus_fare_tmp.iloc[:, 0] + '_' + df_bus_fare_tmp.iloc[:, 1] + '_' +  df_bus_fare_tmp.iloc[:, 2] + '_' +  df_bus_fare_tmp.iloc[:, 3]
    df_bus_fare = df_bus_fare_tmp.sort_values('id').reset_index(drop=True)


    print(datetime.datetime.now().time(),'データ読込終了')
    print(datetime.datetime.now().time(),'バスLOS計算開始')


    #停車パターンリストの作成
    lst_line = list(set(df_bus_nw_tmp.iloc[:, 0] + '_' + df_bus_nw_tmp.iloc[:, 1] + '_' + df_bus_nw_tmp.iloc[:, 2]))
    lst_line.sort()


    #乗換可能バス停の判別
    connect = np.full((len(df_bus_stop), len(df_bus_stop)), 1) - np.eye(len(df_bus_stop))
    np.eye(len(df_bus_stop))
    lst_bus = list(df_bus_stop.iloc[:, -1])

    for line in lst_line:
        #停車パターン別NWの設定
        df_bus_line = df_bus_nw_tmp[df_bus_nw_tmp.iloc[:, 0] + '_' + df_bus_nw_tmp.iloc[:, 1] + '_' + df_bus_nw_tmp.iloc[:, 2] == line].copy() #停車パターン別に抽出
        df_bus_line = df_bus_line.reset_index(drop=True) #インデックスが引き継がれるので振り直し
        jigyo = df_bus_line.iloc[0, 0]
        rosen = df_bus_line.iloc[0, 1]

        #バス停の重複削除
        nam_bus_line = list(set(pd.concat([df_bus_line.iloc[:, 3], df_bus_line.iloc[:, 4]])))
        nam_bus_line.sort()

        #同じ停車パターンに含まれるバス停間は乗換不可
        for ibus in nam_bus_line:
            i = lst_bus.index(jigyo + '_' + ibus)
            for jbus in nam_bus_line:
                j = lst_bus.index(jigyo + '_' + jbus)
                connect[i, j] = 0


    #座標変換
    transformer = pyproj.Transformer.from_crs(src_proj, dst_proj)
    bus_stop_x, bus_stop_y = transformer.transform(df_bus_stop.iloc[:, 2], df_bus_stop.iloc[:, 3])

    #ノードの位置関係を学習
    bus_stop_xy_array = np.array([bus_stop_x, bus_stop_y]).T
    knn_num = len(df_bus_stop) #探索ノード数
    knn_model = NearestNeighbors(n_neighbors = knn_num, algorithm = 'ball_tree').fit(bus_stop_xy_array)

    #バス停別に接続バス停を探索 ひとまず同名バス停かで振り分ける
    lst_connect_same = []
    lst_connect_dif = []
    for ibus in range(len(df_bus_stop)):
        bus_stop_xy = [bus_stop_x[ibus], bus_stop_y[ibus]]
        knn_dists, knn_results = knn_model.kneighbors([bus_stop_xy])

        lst_connect_bus_same = []
        lst_connect_bus_dif = []
        nn = 0
        for ix in range(0, knn_num):
            if knn_dists[:,ix][0] > 100: #100mまでは同一バス停とみなす
                break
            else:
                #乗換候補
                jbus = knn_results[:,ix][0]
                if connect[ibus, jbus] == 1: #同一路線のバス停でない
                    if df_bus_stop.iloc[ibus, 4] == df_bus_stop.iloc[jbus, 4]: #同一名称の場合は同一バス停と認める
                        lst_connect_bus_same.append(jbus)
                    else:
                        lst_connect_bus_dif.append([jbus, knn_dists[:,ix][0]])
        if lst_connect_bus_same == []: #自分自身も含める
            lst_connect_bus_same.append(ibus)
        lst_connect_same.append(lst_connect_bus_same)
        lst_connect_dif.append(lst_connect_bus_dif)
        
    #主要駅等のターミナルで100m以上離れた同名バス停をまとめる
    for ir in range(3): #とりあえず3回
        for ibus in range(len(df_bus_stop)):
            for jbus in lst_connect_same[ibus]:
                lst_connect_same[ibus] = list(set(lst_connect_same[ibus] + lst_connect_same[jbus]))
                lst_connect_same[ibus].sort()

    #別名バス停が同名バス停の同一路線のバス停ではないか確認
    for ibus in range(len(df_bus_stop)):
        for jbus in lst_connect_same[ibus]:
            lst_del = []
            for kbus in lst_connect_dif[ibus]:
                for lbus in lst_connect_same[kbus[0]]:
                    if connect[jbus, lbus] == 0:
                        lst_del.append(kbus)
                        break
            for kbus in lst_del:
                lst_connect_dif[ibus].remove(kbus)


    #同名バス停に従って、別名バス停をまとめる
    for ibus in range(len(df_bus_stop)):
        for jbus in lst_connect_same[ibus]:
            if ibus != jbus:
                lst_connect_dif[ibus] = lst_connect_dif[ibus] + lst_connect_dif[jbus]

    for ibus in range(len(df_bus_stop)):
        lst_connect_dif[ibus].sort(key=lambda x: (x[1], x[0]))


    #別名バス停の接続可能性を検討 別名バス停どうしが同一路線にない（同一路線にある場合は近い方を採用）
    for ibus in range(len(df_bus_stop)):
        flg = [1] * len(lst_connect_dif[ibus])
        lst_del = []
        for jx, jbus in enumerate(lst_connect_dif[ibus][:-1]):
            for kbus in lst_connect_same[jbus[0]]:
                for lx, lbus in enumerate(lst_connect_dif[ibus][jx+1:], 1):
                    if flg[jx + lx] == 1:
                        for mbus in lst_connect_same[lbus[0]]:
                            if connect[kbus, mbus] == 0:
                                flg[jx + lx] = 0
                                lst_del.append(lbus)
                                break
        for i in range(len(lst_del)):
            lst_connect_dif[ibus].remove(lst_del[i])


    #別名バス停が1つの時は、同一バス停とみなす　複数ある場合は別バス停として乗換可能とする
    for ibus in range(len(df_bus_stop)):
        if lst_connect_same[ibus][0] == ibus:
            if len(lst_connect_dif[ibus]) == 0:
                pass
            elif len(lst_connect_dif[ibus]) == 1:
                ix = lst_connect_dif[ibus][0][0]
                if ix < ibus: #既に処理済みのはずなのに存在→ixで複数接続する可能性がある
                    lst_connect_dif[ibus] = []
                elif len(lst_connect_dif[ix]) > 1: #接続相手が複数接続する可能性ある
                    lst_connect_dif[ibus] = []
                elif lst_connect_same[ix][0] < ibus: #既に処理済み
                    lst_connect_dif[ibus] = []
                else:
                    for i in range(len(lst_connect_same[ix])):
                        ii = lst_connect_same[ix][i]
                        lst_connect_same[ibus].append(ii) #同一バス停としてまとめる
                        if i > 0:
                            lst_connect_same[ii] = []
                            lst_connect_same[ii].append(ibus)
                            lst_connect_dif[ii] = []
                    lst_connect_same[ix] = []
                    lst_connect_same[ix].append(ibus)
                    lst_connect_dif[ix] = []
                    lst_connect_dif[ibus] = []
            else:
                for i in range(len(lst_connect_dif[ibus])):
                    lst_connect_dif[ibus][i] = lst_connect_dif[ibus][i][0] #リストから距離を削除
        else:
            lst_connect_same[ibus] = [lst_connect_same[ibus][0]]
            lst_connect_dif[ibus] = []
        
        lst_connect_same[ibus].sort()


    #停車パターン別に経路探索 バス間の平均所要時間と運行本数を算出
    col_name = ['line_id', 'stop_id1', 'stop_id2', 'travel_time', 'fare', 'frequency','seq1','seq2']
    df_bus_line_los = pd.DataFrame(columns=col_name) #停車パータン別LOS用のデータフレーム

    lst_bus = list(df_bus_stop.iloc[:, -1])

    for line in lst_line:
        #停車パターン別NWの設定
        df_bus_line = df_bus_nw_tmp[df_bus_nw_tmp.iloc[:, 0] + '_' + df_bus_nw_tmp.iloc[:, 1] + '_' + df_bus_nw_tmp.iloc[:, 2] == line].copy() #停車パターン別に抽出
        df_bus_line = df_bus_line.reset_index(drop=True) #インデックスが引き継がれるので振り直し
        jigyo = df_bus_line.iloc[0, 0]
        rosen = df_bus_line.iloc[0, 1]

        #バス停の重複削除
        nam_bus_line = list(set(pd.concat([df_bus_line.iloc[:, 3], df_bus_line.iloc[:, 4]])))
        nam_bus_line.sort()

        #所要時間計算 停車パターンで一方向なので、経路探索せずに単純に積み上げ
        tim_line = np.full((len(nam_bus_line), len(nam_bus_line)), 9999.0)
        for i in range(len(df_bus_line)):
            tim = 0.0
            ibus = nam_bus_line.index(df_bus_line.iloc[i, 3])
            for j in range(i + 1, len(df_bus_line) + 1):
                tim = tim + df_bus_line.iloc[j - 1, 5] / 10.0
                jbus = nam_bus_line.index(df_bus_line.iloc[j - 1, 4])
                tim_line[ibus, jbus] = min(tim_line[ibus, jbus], tim) #複数回出現する標柱があるので、短い方にまとめる

        #運賃を決めて、停車パターン別LOSを作成
        lst_dmy = []
        for i, ibus in enumerate(nam_bus_line):
            for j, jbus in enumerate(nam_bus_line):
                if (tim_line[i, j] < 9999.0) and (i != j): #探索不能と2度出てくるバス停を除く
                    if len(df_bus_fare) > 0:
	                    ix = los_calc.bish(jigyo + '_' + rosen + '_' + ibus + '_' + jbus, df_bus_fare.iloc[:,-1])
	                    if ix != -1:
	                        fare = df_bus_fare.iloc[ix, -2]
	                        ii = lst_bus.index(jigyo + '_' + ibus)
	                        ii = lst_connect_same[ii][0]
	                        jj = lst_bus.index(jigyo + '_' + jbus)
	                        jj = lst_connect_same[jj][0]
	                        #停車パターン別なので運行本数は停車パターンで1つ
	                        if round(tim_line[i, j], 0) == 0.0:
	                            tim = 0.5
	                        else:
	                            tim = round(tim_line[i, j], 0)
	                        lst_dmy.append([line,ibus,jbus,tim,fare,df_bus_line.iloc[0, 6],ii,jj])
                    else: #運賃テーブルがない場合
	                        ii = lst_bus.index(jigyo + '_' + ibus)
	                        ii = lst_connect_same[ii][0]
	                        jj = lst_bus.index(jigyo + '_' + jbus)
	                        jj = lst_connect_same[jj][0]
	                        #停車パターン別なので運行本数は停車パターンで1つ
	                        if round(tim_line[i, j], 0) == 0.0:
	                            tim = 0.5
	                        else:
	                            tim = round(tim_line[i, j], 0)
	                        lst_dmy.append([line,ibus,jbus,tim,0,df_bus_line.iloc[0, 6],ii,jj])
        df_bus_line_los = pd.concat([df_bus_line_los, pd.DataFrame(lst_dmy, columns = col_name)], axis=0, ignore_index=True)


    #系統別LOSを集約する
    df_bus_line_los['frequency_tmp'] = np.maximum(1, df_bus_line_los['frequency'].values)
    df_bus_line_los['sumtime'] = df_bus_line_los['travel_time'] * df_bus_line_los['frequency_tmp']
    df_bus_line_los['sumfare'] = df_bus_line_los['fare'] * df_bus_line_los['frequency_tmp']
    df_bus_nw = df_bus_line_los.groupby(['seq1','seq2'])[['sumtime', 'sumfare', 'frequency', 'frequency_tmp']].sum()
    df_bus_nw['travel_time'] = df_bus_nw['sumtime'] / df_bus_nw['frequency_tmp']
    df_bus_nw['fare'] = df_bus_nw['sumfare'] / df_bus_nw['frequency_tmp']
    df_bus_nw['type'] = 1
    col_name = ['seq1', 'seq2', 'travel_time', 'fare', 'frequency', 'type']
    df_bus_nw = df_bus_nw.reset_index().reindex(columns=col_name)


    #乗換リンクを設定
    lst_dmy = []
    col_name = ['seq1', 'seq2', 'travel_time', 'fare', 'frequency', 'type']
    for ibus in range(len(df_bus_stop)):
        for jbus in lst_connect_dif[ibus]:
            lst_dmy.append([ibus,jbus,0,0,0,0])
            df_bus_trans = pd.DataFrame(lst_dmy, columns=col_name)


    #バス停間LOSと乗換リンクを結合してNWを作成
    df_bus_nw = pd.concat([df_bus_nw, df_bus_trans], axis=0, ignore_index=True)


    #print(datetime.datetime.now().time(),'全バス停間探索')
    #バス停間探索
    #ノードSEQの作成
    nam_bus = list(set(pd.concat([df_bus_nw.iloc[:,0],df_bus_nw.iloc[:,1]])))
    #ノードSEQをセット
    lf = []
    for i in range(0, len(df_bus_nw)):
        lf.append(nam_bus.index(df_bus_nw.iloc[i, 0]))
    df_bus_nw['FromノードSEQ'] = lf
    lt = []
    for i in range(0, len(df_bus_nw)):
        lt.append(nam_bus.index(df_bus_nw.iloc[i, 1]))
    df_bus_nw['ToノードSEQ'] = lt

    jla = [0] * (len(nam_bus) + 1)
    jlx = [0] * (len(df_bus_nw) * 2)
    lij = list(df_bus_nw.iloc[:, 5])
    los_calc.forwardstar(len(df_bus_nw), len(nam_bus), list(df_bus_nw.iloc[:, -2]), list(df_bus_nw.iloc[:, -1]), jla, jlx, lij)

    #リンクコストの設定
    #乗車時間
    lvp = df_bus_nw.iloc[:, 2].copy()
    lvm = df_bus_nw.iloc[:, 2].copy()
    #待ち時間を加算
    lvp += np.minimum(tim_limit, np.divide(60.0 * tim_ope / 2.0, df_bus_nw.iloc[:, 4], out=np.zeros_like(df_bus_nw.iloc[:, 4], dtype=np.float64), where=(df_bus_nw.iloc[:, 5] == 1) & (df_bus_nw.iloc[:, 4] == 0)))
    lvm += np.minimum(tim_limit, np.divide(60.0 * tim_ope / 2.0, df_bus_nw.iloc[:, 4], out=np.zeros_like(df_bus_nw.iloc[:, 4], dtype=np.float64), where=(df_bus_nw.iloc[:, 5] == 1) & (df_bus_nw.iloc[:, 4] == 0)))
    #むやみに乗換を増やさないように乗換負荷
    lvp += [ n * tim_load for n in list(df_bus_nw.iloc[:, 5]) ]
    lvm += [ n * tim_load for n in list(df_bus_nw.iloc[:, 5]) ]

    #経路探索
    tim_bus = np.full(len(df_bus_stop) ** 2, 9999.0).reshape(len(df_bus_stop), len(df_bus_stop))
    tim_bus_wait = np.full(len(df_bus_stop) ** 2, 0.0).reshape(len(df_bus_stop), len(df_bus_stop))
    tim_bus_wait_hatu = np.full(len(df_bus_stop) ** 2, 0.0).reshape(len(df_bus_stop), len(df_bus_stop))
    fare_bus = np.full(len(df_bus_stop) ** 2, 9999.0).reshape(len(df_bus_stop), len(df_bus_stop))

    lst_key = list(range(len(df_bus_nw)))
    lst_travel_time = df_bus_nw['travel_time'].to_list()
    lst_fare = df_bus_nw['fare'].to_list()
    lst_frequency = df_bus_nw['frequency'].to_list()
    lst_type = df_bus_nw['type'].to_list()

    dct_travel_time = dict(zip(lst_key, lst_travel_time))
    dct_fare = dict(zip(lst_key, lst_fare))
    dct_frequency = dict(zip(lst_key, lst_frequency))
    dct_type = dict(zip(lst_key, lst_type))


    #乗継なしで行けるバス停間のLOSをセット
    for i in range(len(df_bus_nw) - len(df_bus_trans)):
        ibus = df_bus_nw.iloc[i, 0]
        jbus = df_bus_nw.iloc[i, 1]
        tim_bus[ibus, jbus] = df_bus_nw.iloc[i, 2]
        if df_bus_nw.iloc[i, 4] != 0:
            tim_bus_wait[ibus, jbus] = min(60.0 * tim_ope / df_bus_nw.iloc[i, 4] / 2.0, tim_limit)
            tim_bus_wait_hatu[ibus, jbus] = min(60.0 * tim_ope / df_bus_nw.iloc[i, 4] / 2.0, tim_limit)
        fare_bus[ibus, jbus] = df_bus_nw.iloc[i, 3]

    for ibus in range(len(nam_bus)):
        ndin = ibus #探索起点
        minv = [math.inf] * len(nam_bus)
        nxt = [-1] * len(nam_bus)
        lno = [0] * len(nam_bus)

        #ダイクストラ法による最短経路探索
        los_calc.dijkstra_bus(ndin, len(nam_bus), minv, list(df_bus_nw.iloc[:, -2]), list(df_bus_nw.iloc[:, -1]), lvp, lvm, jla, jlx, nxt, lno, list(df_bus_nw.iloc[:, -3]))

        for jbus in range(len(nam_bus)):
            if ibus == jbus: continue
            if tim_bus[nam_bus[ibus], nam_bus[jbus]] < 9999.0: continue #乗継なしで行けるバス停間は探索しない
            ndtb = []
            lktb = []
            ierr, ir, tim_bus[nam_bus[ibus], nam_bus[jbus]], tim_bus_wait[nam_bus[ibus], nam_bus[jbus]], tim_bus_wait_hatu[nam_bus[ibus], nam_bus[jbus]], fare_bus[nam_bus[ibus], nam_bus[jbus]] = los_calc.rotout_bus(ibus, jbus, nxt, lno, ndtb, lktb, dct_travel_time, dct_fare, dct_frequency, dct_type, tim_limit, tim_ope)


    #バスアクセス算出
    znbus = [] #ゾーン別アクセスバスのリスト
    dist_znbus = [] #ゾーン別アクセスバスへの距離リスト
    transformer = pyproj.Transformer.from_crs(src_proj, dst_proj)
    #座標変換
    zn_x, zn_y = transformer.transform(df_zn.iloc[:, 1], df_zn.iloc[:, 2])

    for zn in range(0, len(df_zn)):
        zn_xy = [zn_x[zn], zn_y[zn]]
        knn_dists, knn_results = knn_model.kneighbors([zn_xy])

        lst_bus = []
        lst_dist = []

        #最大5kmまで500m単位で範囲を広げて、アクセスする駅を特定
        maxdist = math.ceil(knn_dists[:,0][0] / 500) #最寄り駅
        if maxdist > 5:
            pass
        else:
            for ix in range(0, knn_num):
                if knn_dists[:,ix][0] / 500 > maxdist:
                    break
                else:
                    lst_bus.append(knn_results[:,ix][0])
                    lst_dist.append(knn_dists[:,ix][0])
        znbus.append(lst_bus)
        dist_znbus.append(lst_dist)


    #ゾーン間LOSを計算
    #出力用のデータフレームを準備
    df_los = pd.DataFrame(columns=['Travel_Time_Bus', 'Waiting_Time_Bus', 'Access_Time_Bus', 'Egress_Time_Bus', 'Fare_Bus'])
    lst_jz = df_zn.iloc[:, 0]

    for iz in range(0, len(df_zn)):
        lst_los = []
        for jz in range(0, len(df_zn)):
            sumtim = 9999.0
            min_i = len(df_bus_stop)
            min_j = len(df_bus_stop)
            if iz == jz:
                lst_los.append([0.0,0.0,0.0,0.0,0.0])
            else:
                for i, bus_acs in enumerate(znbus[iz]):
                    for j, bus_egr in enumerate(znbus[jz]):
                        ibus = lst_connect_same[bus_acs][0]
                        jbus = lst_connect_same[bus_egr][0]
                        if sumtim > tim_bus[ibus, jbus] + tim_bus_wait[ibus, jbus] + \
                                    dist_znbus[iz][i] * math.sqrt(2) / 80.0 + \
                                    dist_znbus[jz][j] * math.sqrt(2) / 80.0:
                            sumtim = tim_bus[ibus, jbus] + tim_bus_wait[ibus, jbus] + \
                                    dist_znbus[iz][i] * math.sqrt(2) / 80.0 + \
                                    dist_znbus[jz][j] * math.sqrt(2) / 80.0
                            min_i = i
                            min_j = j
                if sumtim == 9999.0:
                    lst_los.append([9999.0,9999.0,9999.0,9999.0,9999.0])
                else:
                    ibus = lst_connect_same[znbus[iz][min_i]][0]
                    jbus = lst_connect_same[znbus[jz][min_j]][0]
                    lst_los.append([round(tim_bus[ibus, jbus], 1),round(tim_bus_wait[ibus, jbus] - tim_bus_wait_hatu[ibus, jbus] + tim_wait, 1),round(dist_znbus[iz][min_i] * math.sqrt(2) / 80.0, 1),round(dist_znbus[jz][min_j] * math.sqrt(2) / 80.0, 1),round(fare_bus[ibus, jbus], 1)])

        df_los_zn = pd.DataFrame(lst_los, columns=['Travel_Time_Bus', 'Waiting_Time_Bus', 'Access_Time_Bus', 'Egress_Time_Bus', 'Fare_Bus'])
        df_los = pd.concat([df_los, df_los_zn], axis=0, ignore_index=True)

    print(datetime.datetime.now().time(),'バスLOS計算終了')
    return df_los


def los_dmy(df_zn):
    df_los = pd.DataFrame(columns=['Travel_Time_Bus', 'Waiting_Time_Bus', 'Access_Time_Bus', 'Egress_Time_Bus', 'Fare_Bus'])
    
    for iz in range(0, len(df_zn)):
        lst_los = []
        for jz in range(0, len(df_zn)):
            if iz == jz:
                lst_los.append([0.0,0.0,0.0,0.0,0.0])
            else:
                lst_los.append([9999.0,9999.0,9999.0,9999.0,9999.0])

        df_los_zn = pd.DataFrame(lst_los, columns=['Travel_Time_Bus', 'Waiting_Time_Bus', 'Access_Time_Bus', 'Egress_Time_Bus', 'Fare_Bus'])
        df_los = pd.concat([df_los, df_los_zn], axis=0, ignore_index=True)
    return df_los
