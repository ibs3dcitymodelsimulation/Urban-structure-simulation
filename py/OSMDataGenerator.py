

import osmnx as ox

# control.txtの読み込み
with open('control.txt', 'r') as f:
    fn = f.readline().strip()
    
# 対象地域の道路情報取得
G = ox.graph_from_place(f'{fn}', network_type="drive")

# 出力
ox.save_graph_shapefile(G)

