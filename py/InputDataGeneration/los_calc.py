#coding:Shift_Jis
import math
'''
バイナリサーチ
  value:検索値
  data:検索対象リスト
'''
def bish(value, data):
    left = 0
    right = len(data) - 1
    while left <= right:
        mid = (left + right) // 2
        if value == data[mid]: # 見つかった
            return mid
        elif value > data[mid]:
            left = mid + 1
        else:
            right = mid - 1
    return -1 # 未検出


'''
道路NWのリンク接続情報をforward star形式に変換
  nlink:リンク数
  nnode:ノード数
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  lij:方向フラグ
  nopass:不通過フラグ
'''
def forwardstar_car(nlink, nnode, lfr, lto, jla, jlx, lij, nopass):
    #各ノードの接続リンク数を算出
    for lx in range(nlink):
        if nopass[lx] == 1: #通行不可
            continue
        elif lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jla[lf + 1] = jla[lf + 1] + 1
            lt = lto[lx]
            jla[lt + 1] = jla[lt + 1] + 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jla[lf + 1] = jla[lf + 1] + 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jla[lt + 1] = jla[lt + 1] + 1
    
    #各ノードの接続情報のポインタを設定
    for nx in range(nnode):
        jla[nx + 1] = jla[nx + 1] + jla[nx]
    
    #各ノードの接続リンクを設定
    for lx in range(nlink):
        if nopass[lx] == 1: #通行不可
            continue
        elif lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jl = jla[lf]
            jlx[jl] = lx + 1
            jla[lf] = jla[lf] + 1
            lt = lto[lx]
            jl = jla[lt]
            jlx[jl] = -(lx + 1)
            jla[lt] = jla[lt] + 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jl = jla[lf]
            jlx[jl] = lx + 1
            jla[lf] = jla[lf] + 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jl = jla[lt]
            jlx[jl] = -(lx + 1)
            jla[lt] = jla[lt] + 1
            
    #各ノードの接続リンクを設定で変更された各ノードの接続リンク数を元に戻す
    for lx in range(nlink):
        if nopass[lx] == 1: #通行不可
            continue
        elif lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jla[lf] = jla[lf] - 1
            lt = lto[lx]
            jla[lt] = jla[lt] - 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jla[lf] = jla[lf] - 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jla[lt] = jla[lt] - 1
    return


'''
ダイクストラ法による自動車LOS用の最短経路探索
  ndin:探索始点ノード
  nnode:ノード数
  minv:最短経路コスト
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  lvp:始点ノードSEQ
  lvm:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
'''
def dijkstra_car(ndin, nnode, minv, lfr, lto, lvp, lvm, jla, jlx, nxt, lno):
    #初期化
    mx = nnode + 1
    lbl = [mx] * nnode
    npo = [mx] * nnode
    no = ndin #始点
    minv[no] = 0 #始点のコスト
    lbl[no] = -1 #始点は探索済
    nxt[no] = 0 #始点は接続先なし
    nmin = mx #最小コストノード
    nmax = mx #最大コストノード

    while True:
        #リンクの向きを考慮してコスト計算
        for jl in range(jla[no], jla[no + 1]):
            ln = jlx[jl]
            if ln == 0: #通行不可
                continue
            elif ln > 0: #From→To
                nx = lto[ln - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvp[ln - 1]
            elif ln < 0: #To→From
                nx = lfr[abs(ln) - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvm[abs(ln) - 1]

            if lv < minv[nx]:
                if nmin == mx: #探索候補集合が空
                    nmax = nx
                    nmin = nx
                    npo[nx] = mx #ノードnxよりコストが小さいノードはない
                elif nmin == nx: #最小コストノードのコストが更新
                    pass
                else:
                    if minv[nx] == math.inf: #当該ノードが初めて探索された コストが最大と仮定
                        nn = nmax
                    else:
                        nn = npo[nx]
                        if nmax == nx: #最大コストのノードのコストが更新　コストが最大から1つ前になると仮定
                            nmax = npo[nx]
                        else: #nxを取り出して前後を繋ぎ変え
                            np = lbl[nx]
                            npo[np] = npo[nx]    
                        lbl[nn] = lbl[nx]

                    while True: #探索ノードの繋ぎを確定させる
                        if minv[nn] > lv:
                            nn = npo[nn]
                            if nn == mx:
                                lbl[nx] = nmin
                                npo[nmin] = nx
                                nmin = nx
                                npo[nx] = mx
                                break
                        else:
                            lbl[nx] = lbl[nn]
                            lbl[nn] = nx
                            npo[nx] = nn
                            if lbl[nx] == mx:
                                nmax = nx
                            else:
                                nj = lbl[nx]
                                npo[nj] = nx
                            break

                minv[nx] = lv
                nxt[nx] = no
                lno[nx] = ln
            else:
                continue


        if nmin == mx: #全ノードの経路決定したため探索終了
            break
        else: #最小コストが決まったノードを未確定ノードリストから取り出す
            no = nmin
            nmin = lbl[no]
            lbl[no] = -1
            if nmin != mx:
                npo[nmin] = mx
    return


'''
鉄道NWとバスNW用のリンク接続情報をforward star形式に変換
  nlink:リンク数
  nnode:ノード数
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  lij:方向フラグ
'''
def forwardstar(nlink, nnode, lfr, lto, jla, jlx, lij):
    #各ノードの接続リンク数を算出
    for lx in range(nlink):
        if lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jla[lf + 1] = jla[lf + 1] + 1
            lt = lto[lx]
            jla[lt + 1] = jla[lt + 1] + 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jla[lf + 1] = jla[lf + 1] + 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jla[lt + 1] = jla[lt + 1] + 1
    
    #各ノードの接続情報のポインタを設定
    for nx in range(nnode):
        jla[nx + 1] = jla[nx + 1] + jla[nx]
    
    #各ノードの接続リンクを設定
    for lx in range(nlink):
        if lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jl = jla[lf]
            jlx[jl] = lx + 1
            jla[lf] = jla[lf] + 1
            lt = lto[lx]
            jl = jla[lt]
            jlx[jl] = -(lx + 1)
            jla[lt] = jla[lt] + 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jl = jla[lf]
            jlx[jl] = lx + 1
            jla[lf] = jla[lf] + 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jl = jla[lt]
            jlx[jl] = -(lx + 1)
            jla[lt] = jla[lt] + 1
            
    #各ノードの接続リンクを設定で変更された各ノードの接続リンク数を元に戻す
    for lx in range(nlink):
        if lij[lx] == -1: #通行不可
            continue
        elif lij[lx] == 0: #両方向リンク
            lf = lfr[lx]
            jla[lf] = jla[lf] - 1
            lt = lto[lx]
            jla[lt] = jla[lt] - 1
        elif lij[lx] == 1: #From→To
            lf = lfr[lx]
            jla[lf] = jla[lf] - 1
        elif lij[lx] == 2: #To→From
            lt = lto[lx]
            jla[lt] = jla[lt] - 1
    return


'''
ダイクストラ法による鉄道路線別最短経路探索
  ndin:探索始点ノード
  nnode:ノード数
  minv:最短経路コスト
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  lvp:始点ノードSEQ
  lvm:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  lktype:リンク種別
'''
def dijkstra_rail_line(ndin, nnode, minv, lfr, lto, lvp, lvm, jla, jlx, nxt, lno, lktype):
    #初期化
    mx = nnode + 1
    lbl = [mx] * nnode
    npo = [mx] * nnode
    no = ndin #始点
    minv[no] = 0 #始点のコスト
    lbl[no] = -1 #始点は探索済
    nxt[no] = 0 #始点は接続先なし
    nmin = mx #最小コストノード
    nmax = mx #最大コストノード

    while True:
        #リンクの向きを考慮してコスト計算
        for jl in range(jla[no], jla[no + 1]):
            ln = jlx[jl]
            if lno[no] != 0: #lno[no]が0のとき、lktype[- 1]となるため、最後の要素の参照を避ける
                if lktype[abs(lno[no]) - 1] == 2 and lktype[abs(ln) - 1] == 2: continue #自路線乗換リンクを使わない列車種別の乗換を禁止
                if lktype[abs(lno[no]) - 1] == 2 and lktype[abs(ln) - 1] == 3: continue #駅ダミーノードへ当該駅ダミーリンクを使わない乗車を禁止
                if lktype[abs(lno[no]) - 1] == 3 and lktype[abs(ln) - 1] == 2: continue #駅ダミーノードへ当該駅ダミーリンクを使わない降車を禁止
                if lktype[abs(lno[no]) - 1] == 3 and lktype[abs(ln) - 1] == 3: continue #複数の列車種別をまたぐ自路線乗換を禁止
            if ln == 0: #通行不可
                continue
            elif ln > 0: #From→To
                nx = lto[ln - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvp[ln - 1]
            elif ln < 0: #To→From
                nx = lfr[abs(ln) - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvm[abs(ln) - 1]

            if lv < minv[nx]:
                if nmin == mx: #探索候補集合が空
                    nmax = nx
                    nmin = nx
                    npo[nx] = mx #ノードnxよりコストが小さいノードはない
                elif nmin == nx: #最小コストノードのコストが更新
                    pass
                else:
                    if minv[nx] == math.inf: #当該ノードが初めて探索された コストが最大と仮定
                        nn = nmax
                    else:
                        nn = npo[nx]
                        if nmax == nx: #最大コストのノードのコストが更新　コストが最大から1つ前になると仮定
                            nmax = npo[nx]
                        else: #nxを取り出して前後を繋ぎ変え
                            np = lbl[nx]
                            npo[np] = npo[nx]    
                        lbl[nn] = lbl[nx]

                    while True: #探索ノードの繋ぎを確定させる
                        if minv[nn] > lv:
                            nn = npo[nn]
                            if nn == mx:
                                lbl[nx] = nmin
                                npo[nmin] = nx
                                nmin = nx
                                npo[nx] = mx
                                break
                        else:
                            lbl[nx] = lbl[nn]
                            lbl[nn] = nx
                            npo[nx] = nn
                            if lbl[nx] == mx:
                                nmax = nx
                            else:
                                nj = lbl[nx]
                                npo[nj] = nx
                            break

                minv[nx] = lv
                nxt[nx] = no
                lno[nx] = ln
            else:
                continue


        if nmin == mx: #全ノードの経路決定したため探索終了
            break
        else: #最小コストが決まったノードを未確定ノードリストから取り出す
            no = nmin
            nmin = lbl[no]
            lbl[no] = -1
            if nmin != mx:
                npo[nmin] = mx
    return


'''
鉄道路線別探索経路の出力
  iz:出発地
  jz:目的地
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  ir:最短経路のリンク数
  ndtb:最短経路ノードリスト
  lktb:最短経路リンクリスト
  lktype:リンク種別
  lkexp:列車種別
  lkfreq:運行本数
'''
def rotout_rail_line(iz, jz, nxt, lno, ndtb, lktb, lktype, lkexp, lkfreq):
    ierr = 0
    ir = 0
    hon = 999
    railtype = 1
    nx = jz
    ndtb.append(nx)
    while nx != iz: #目的地から出発地まで追いかける
        ir = ir + 1
        if nxt[nx] == -1:
            ierr = 999
            break
        else:
            ln = lno[nx]
            if lktype[abs(ln) - 1] == 1:
                if lkexp[abs(ln) - 1] != 1:
                    railtype = lkexp[abs(ln) - 1]
                hon = min(hon, lkfreq[abs(ln) - 1])
            lktb.append(ln)
            nx = nxt[nx]
            ndtb.append(nx)
    return ierr, ir, railtype, hon  #エラー,リンク数,列車種別,運行本数


'''
ダイクストラ法による鉄道の全駅間の最短経路探索
  ndin:探索始点ノード
  nnode:ノード数
  minv:最短経路コスト
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  lvp:始点ノードSEQ
  lvm:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  lktype:リンク種別
'''
def dijkstra_rail(ndin, nnode, minv, lfr, lto, lvp, lvm, jla, jlx, nxt, lno, lktype):
    #初期化
    mx = nnode + 1
    lbl = [mx] * nnode
    npo = [mx] * nnode
    no = ndin #始点
    minv[no] = 0 #始点のコスト
    lbl[no] = -1 #始点は探索済
    nxt[no] = 0 #始点は接続先なし
    nmin = mx #最小コストノード
    nmax = mx #最大コストノード

    while True:
        #リンクの向きを考慮してコスト計算
        for jl in range(jla[no], jla[no + 1]):
            ln = jlx[jl]
            if lno[no] != 0: #lno[no]が0のとき、lktype[- 1]となるため、最後の要素の参照を避ける
                if lktype[abs(lno[no]) - 1] == 1 and lktype[abs(ln) - 1] == 1: continue #折り返し乗車を禁止
                if lktype[abs(lno[no]) - 1] == 4 and lktype[abs(ln) - 1] == 4: continue #乗換リンクの連続を禁止
            if ln == 0: #通行不可
                continue
            elif ln > 0: #From→To
                nx = lto[ln - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvp[ln - 1]
            elif ln < 0: #To→From
                nx = lfr[abs(ln) - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvm[abs(ln) - 1]

            if lv < minv[nx]:
                if nmin == mx: #探索候補集合が空
                    nmax = nx
                    nmin = nx
                    npo[nx] = mx #ノードnxよりコストが小さいノードはない
                elif nmin == nx: #最小コストノードのコストが更新
                    pass
                else:
                    if minv[nx] == math.inf: #当該ノードが初めて探索された コストが最大と仮定
                        nn = nmax
                    else:
                        nn = npo[nx]
                        if nmax == nx: #最大コストのノードのコストが更新　コストが最大から1つ前になると仮定
                            nmax = npo[nx]
                        else: #nxを取り出して前後を繋ぎ変え
                            np = lbl[nx]
                            npo[np] = npo[nx]    
                        lbl[nn] = lbl[nx]

                    while True: #探索ノードの繋ぎを確定させる
                        if minv[nn] > lv:
                            nn = npo[nn]
                            if nn == mx:
                                lbl[nx] = nmin
                                npo[nmin] = nx
                                nmin = nx
                                npo[nx] = mx
                                break
                        else:
                            lbl[nx] = lbl[nn]
                            lbl[nn] = nx
                            npo[nx] = nn
                            if lbl[nx] == mx:
                                nmax = nx
                            else:
                                nj = lbl[nx]
                                npo[nj] = nx
                            break

                minv[nx] = lv
                nxt[nx] = no
                lno[nx] = ln
            else:
                continue


        if nmin == mx: #全ノードの経路決定したため探索終了
            break
        else: #最小コストが決まったノードを未確定ノードリストから取り出す
            no = nmin
            nmin = lbl[no]
            lbl[no] = -1
            if nmin != mx:
                npo[nmin] = mx
    return


'''
全駅間探索経路の出力
  iz:出発地
  jz:目的地
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  ir:最短経路のリンク数
  ndtb:最短経路ノードリスト
  lktb:最短経路リンクリスト
  lst_station:駅コード
  len_agency:事業者コードの文字列長
  df_rail_nw:鉄道NW
  df_rail_fare_dist:運賃テーブル(距離)
  df_rail_fare_sec:運賃テーブル(特定区間)
'''
def rotout_rail(iz, jz, nxt, lno, ndtb, lktb, lst_station, len_agency, df_rail_nw, df_rail_fare_dist, df_rail_fare_sec):
    ierr = 0
    ir = 0
    tim_rail = 0.0
    tim_wait = 0.0
    fare_rail = 0.0
    dist_ope = 0.0 #営業キロ
    dist_fare = 0.0 #運賃計算キロ
    fareflg = 0 #幹線フラグ
    
    nx = jz
    ista = ''
    jsta = lst_station[jz]
    ndtb.append(nx)
    while nx != iz: #目的地から出発地まで追いかける
        ir = ir + 1
        if nxt[nx] == -1:
            ierr = 999
            break
        else:
            ln = lno[nx]
            lktb.append(ln)

            
            #幹線時間を積み上げ
            if ln > 0:
                tim_rail += df_rail_nw.iloc[ln - 1, 7]
            else:
                tim_rail += df_rail_nw.iloc[abs(ln) - 1, 8]
            
            if df_rail_nw.iloc[abs(ln) - 1, 3] == 4: #乗換リンク
                if ir == 1: #最後が乗換を禁止
                    tim_rail = 9999.0
                    tim_wait = 0.0
                    fare_rail = 9999.0
                    return ierr, ir, tim_rail, tim_wait, fare_rail
                if lst_station[nx][0:len_agency] == lst_station[nxt[nx]][0:len_agency]: #同一事業者の乗換
                    pass
                else:
                    #運賃計算
                    fare_rail += calc_fare_rail(ista, jsta, fareflg, dist_ope, dist_fare, df_rail_fare_dist, df_rail_fare_sec, len_agency)
                    
                    #初期化
                    dist_ope = 0.0
                    dist_fare = 0.0
                    fareflg = 0
                    jsta = lst_station[nxt[nx]]
            else: #幹線リンク
                if ln > 0:
                    #乗車待ち時間の積み上げ
                    if df_rail_nw.iloc[ln - 1, 9] > 0: #運行本数がない場合は待ち時間を計算しない
                        tim_wait += 60.0 / df_rail_nw.iloc[ln - 1, 9] / 2.0
                else:
                    #乗車待ち時間の積み上げ
                    if df_rail_nw.iloc[abs(ln) - 1, 10] > 0: #運行本数がない場合は待ち時間を計算しない
                        tim_wait += 60.0 / df_rail_nw.iloc[abs(ln) - 1, 10] / 2.0
                    
                #運賃計算のための距離積み上げ
                dist_ope += df_rail_nw.iloc[abs(ln) - 1, 5]
                if df_rail_nw.iloc[abs(ln) - 1, 6] == 0.0:
                    dist_fare += df_rail_nw.iloc[abs(ln) - 1, 5]
                else:
                    dist_fare += df_rail_nw.iloc[abs(ln) - 1, 6]
                
                #幹線or地方判定　0:初期値,1:幹線のみ,2:地方のみ,3:幹線+地方
                if fareflg == 0:
                    if df_rail_nw.iloc[abs(ln) - 1, 6] == 0.0:
                        fareflg = 1
                    else:
                        fareflg = 2
                elif fareflg == 1:
                    if df_rail_nw.iloc[abs(ln) - 1, 6] == 0.0:
                        pass
                    else:
                        fareflg = 3
                elif fareflg == 2:
                    if df_rail_nw.iloc[abs(ln) - 1, 6] == 0.0:
                        fareflg = 3
                    else:
                        pass
                else:
                    pass
                
                ista = lst_station[nxt[nx]]
            nx = nxt[nx]
            ndtb.append(nx)
            
    if df_rail_nw.iloc[abs(ln) - 1, 3] == 4: #最初が乗換を禁止
        tim_rail = 9999.0
        tim_wait = 0.0
        fare_rail = 9999.0
    else: #最終乗車区間の運賃計算
        fare_rail += calc_fare_rail(ista, jsta, fareflg, dist_ope, dist_fare, df_rail_fare_dist, df_rail_fare_sec, len_agency)
    return ierr, ir, tim_rail, tim_wait, fare_rail  #エラー,リンク数,幹線時間,乗車待ち時間,運賃


'''
鉄道運賃計算
  ista:乗車駅コード
  jsta:降車駅コード
  fareflg:利用路線フラグ
  dist_ope:営業キロ
  dist_fare:運賃計算キロ
  fare_rail:運賃
  df_rail_fare_dist:運賃テーブル(距離)
  df_rail_fare_sec:運賃テーブル(特定区間)
  len_agency:事業者コードの文字列長
'''
def calc_fare_rail(ista, jsta, fareflg, dist_ope, dist_fare, df_rail_fare_dist, df_rail_fare_sec, len_agency):
    fare = 0.0
    if (df_rail_fare_sec.iloc[:, 5] == ista + jsta).any(): #区間運賃テーブルを確認
        fare = df_rail_fare_sec[df_rail_fare_sec.iloc[:, 5] == ista + jsta].iloc[0, 2]
    elif (df_rail_fare_sec.iloc[:, 5] == jsta + ista).any(): #区間運賃テーブルを確認
        fare = df_rail_fare_sec[df_rail_fare_sec.iloc[:, 5] == jsta + ista].iloc[0, 2]
    else: #対距離運賃テーブルを確認
        if (dist_ope == 0) or (len(df_rail_fare_dist) == 0): #鉄道NWに距離データがないもしくは距離帯テーブルがない場合は運賃を計算しない
            return fare
        else:
            if ista[0:len_agency] == '1'.zfill(len_agency): #JR
                if fareflg == 1: #幹線のみ
                    fare = df_rail_fare_dist[(df_rail_fare_dist.iloc[:, 0] == ista[0:len_agency]) & \
                                             (df_rail_fare_dist.iloc[:, 1] == 1) & \
                                             (df_rail_fare_dist.iloc[:, 2] == math.ceil(dist_ope))].iloc[0, 3]
                elif fareflg == 2: #地方のみ
                    fare = df_rail_fare_dist[(df_rail_fare_dist.iloc[:, 0] == ista[0:len_agency]) & \
                                             (df_rail_fare_dist.iloc[:, 1] == 2) & \
                                             (df_rail_fare_dist.iloc[:, 2] == math.ceil(dist_ope))].iloc[0, 3]
                else: #幹線+地方
                    if dist_ope <= 10.0:
                        fare = df_rail_fare_dist[(df_rail_fare_dist.iloc[:, 0] == ista[0:len_agency]) & \
                                                 (df_rail_fare_dist.iloc[:, 1] == 2) & \
                                                 (df_rail_fare_dist.iloc[:, 2] == math.ceil(dist_ope))].iloc[0, 3]
                    else:
                        fare = df_rail_fare_dist[(df_rail_fare_dist.iloc[:, 0] == ista[0:len_agency]) & \
                                                 (df_rail_fare_dist.iloc[:, 1] == 1) & \
                                                 (df_rail_fare_dist.iloc[:, 2] == math.ceil(dist_fare))].iloc[0, 3]
            else:
                fare = df_rail_fare_dist[(df_rail_fare_dist.iloc[:, 0] == ista[0:len_agency]) & \
                                         (df_rail_fare_dist.iloc[:, 2] == math.ceil(dist_ope))].iloc[0, 3]
    return fare


'''
ダイクストラ法による全バス停間の最短経路探索
  ndin:探索始点ノード
  nnode:ノード数
  minv:最短経路コスト
  lfr:始点ノードSEQ
  lto:終点ノードSEQ
  lvp:始点ノードSEQ
  lvm:終点ノードSEQ
  jla:リンク接続情報（枝数）
  jlx:リンク接続情報（リンクSEQ）
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  lktype:リンク種別
'''
def dijkstra_bus(ndin, nnode, minv, lfr, lto, lvp, lvm, jla, jlx, nxt, lno, lktype):
    #初期化
    mx = nnode + 1
    lbl = [mx] * nnode
    npo = [mx] * nnode
    no = ndin #始点
    minv[no] = 0 #始点のコスト
    lbl[no] = -1 #始点は探索済
    nxt[no] = 0 #始点は接続先なし
    nmin = mx #最小コストノード
    nmax = mx #最大コストノード

    while True:
        #リンクの向きを考慮してコスト計算
        for jl in range(jla[no], jla[no + 1]):
            ln = jlx[jl]
            if lno[no] != 0: #lno[no]が0のとき、lktype[- 1]となるため、最後の要素の参照を避ける
                if lktype[abs(lno[no]) - 1] == 0 and lktype[abs(ln) - 1] == 0: continue #乗換リンクの連続を禁止
            if ln == 0: #通行不可
                continue
            elif ln > 0: #From→To
                nx = lto[ln - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvp[ln - 1]
            elif ln < 0: #To→From
                nx = lfr[abs(ln) - 1]
                if lbl[nx] < 0: #経路確定済みノード
                    continue
                else:
                    lv = minv[no] + lvm[abs(ln) - 1]

            if lv < minv[nx]:
                if nmin == mx: #探索候補集合が空
                    nmax = nx
                    nmin = nx
                    npo[nx] = mx #ノードnxよりコストが小さいノードはない
                elif nmin == nx: #最小コストノードのコストが更新
                    pass
                else:
                    if minv[nx] == math.inf: #当該ノードが初めて探索された コストが最大と仮定
                        nn = nmax
                    else:
                        nn = npo[nx]
                        if nmax == nx: #最大コストのノードのコストが更新　コストが最大から1つ前になると仮定
                            nmax = npo[nx]
                        else: #nxを取り出して前後を繋ぎ変え
                            np = lbl[nx]
                            npo[np] = npo[nx]    
                        lbl[nn] = lbl[nx]

                    while True: #探索ノードの繋ぎを確定させる
                        if minv[nn] > lv:
                            nn = npo[nn]
                            if nn == mx:
                                lbl[nx] = nmin
                                npo[nmin] = nx
                                nmin = nx
                                npo[nx] = mx
                                break
                        else:
                            lbl[nx] = lbl[nn]
                            lbl[nn] = nx
                            npo[nx] = nn
                            if lbl[nx] == mx:
                                nmax = nx
                            else:
                                nj = lbl[nx]
                                npo[nj] = nx
                            break

                minv[nx] = lv
                nxt[nx] = no
                lno[nx] = ln
            else:
                continue


        if nmin == mx: #全ノードの経路決定したため探索終了
            break
        else: #最小コストが決まったノードを未確定ノードリストから取り出す
            no = nmin
            nmin = lbl[no]
            lbl[no] = -1
            if nmin != mx:
                npo[nmin] = mx
    return


'''
全バス停間探索経路の出力
  iz:出発地
  jz:目的地
  nxt:最短経路接続ノード
  lno:最短経路接続リンク番号
  ir:最短経路のリンク数
  ndtb:最短経路ノードリスト
  lktb:最短経路リンクリスト
  dct_travel_time:所要時間
  dct_fare:運賃
  dct_frequency:運行本数
  dct_type:リンクタイプ
  tim_limit:待ち時間の上限
  tim_ope:運行時間
'''
def rotout_bus(iz, jz, nxt, lno, ndtb, lktb, dct_travel_time, dct_fare, dct_frequency, dct_type, tim_limit, tim_ope):
    ierr = 0
    ir = 0
    tim = 0.0
    tim_wait = 0.0
    tim_wait_hatu = 0.0
    fare = 0.0
    
    nx = jz
    ndtb.append(nx)
    while nx != iz: #目的地から出発地まで追いかける
        ir = ir + 1
        if nxt[nx] == -1:
            ierr = 999
            tim = 9999.0
            tim_wait = 0.0
            tim_wait_hatu = 0.0
            fare = 9999.0
            return ierr, ir, tim, tim_wait, tim_wait_hatu, fare
        else:
            ln = lno[nx]
            lktb.append(ln)

            
            #時間、運賃を積み上げ
            if ln > 0:
                tim += dct_travel_time[ln - 1]
                fare += dct_fare[ln - 1]
            else:
                tim += dct_travel_time[abs(ln) - 1]
                fare += dct_fare[abs(ln) - 1]
            
            if dct_type[abs(ln) - 1] == 0: #乗換リンク
                if ir == 1: #最後が乗換を禁止
                    tim = 9999.0
                    tim_wait = 0.0
                    tim_wait_hatu = 0.0
                    fare = 9999.0
                    return ierr, ir, tim, tim_wait, tim_wait_hatu, fare
            else: #幹線リンク
                if ln > 0:
                    #乗車待ち時間の積み上げ
                    if dct_frequency[ln - 1] != 0:
                        tim_wait += min(60.0 * tim_ope / dct_frequency[ln - 1] / 2.0, tim_limit)
                else:
                    #乗車待ち時間の積み上げ
                    if dct_frequency[abs(ln) - 1] != 0:
                        tim_wait += min(60.0 * tim_ope / dct_frequency[abs(ln) - 1] / 2.0, tim_limit)
            nx = nxt[nx]
            ndtb.append(nx)
            
    if dct_type[abs(ln) - 1] == 0: #最初が乗換を禁止
        tim = 9999.0
        tim_wait = 0.0
        tim_wait_hatu = 0.0
        fare = 9999.0
        return ierr, ir, tim, tim_wait, tim_wait_hatu, fare

    if ln > 0:
        if dct_frequency[ln - 1] != 0:
                tim_wait_hatu = min(60.0 * tim_ope / dct_frequency[ln - 1] / 2.0, tim_limit)
    else:
        if dct_frequency[abs(ln) - 1] != 0:
                tim_wait_hatu = min(60.0 * tim_ope / dct_frequency[abs(ln) - 1] / 2.0, tim_limit)
    
    return ierr, ir, tim, tim_wait, tim_wait_hatu, fare #エラー,リンク数,幹線時間,乗車待ち時間,初乗り待ち時間,運賃
