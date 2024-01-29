#coding:Shift_Jis
import sys
import os
import csv
import pandas as pd
import geopandas as gpd
import datetime
import warnings
import los_car
import los_rail
import los_bus

warnings.simplefilter('ignore', FutureWarning)

curdir = os.getcwd()
#フォルダ構成の読込
infile = curdir + '/Control_Input.txt'
rf = open(infile, 'r', encoding='Shift_Jis')
indir = rf.readline().rstrip('\n')
outdir = rf.readline().rstrip('\n')
cnvproj = rf.readline().rstrip('\n')

if os.path.isdir(indir) != True:
    print('インプットフォルダ:'+ indir + 'がありません')
    os.system('PAUSE')
    sys.exit()

if os.path.isdir(outdir) != True:
    print('アウトプットフォルダ:' + outdir + 'がありません')
    os.system('PAUSE')
    sys.exit()

path_ofile = outdir + '/Zone_TravelTime.csv' #探索結果出力ファイル


#座標系の設定
src_proj = 'EPSG:6697' #変換前座標系 緯度経度JGD2011
dst_proj = 'EPSG:' + cnvproj #変換後座標系


#ゾーンデータは全機関で使用するので、先に読み込む
path_shp_zn = indir + '/Zone_Polygon.shp' #ゾーンのshp
#ゾーンデータ読込
if os.path.exists(path_shp_zn) != True:
    print('ゾーンshp:' + path_shp_zn + 'がありません')
    os.system('PAUSE')
    sys.exit()
print(datetime.datetime.now().time(),'ゾーンデータ読込：' + path_shp_zn)
gdf = gpd.read_file(path_shp_zn)
#ゾーンデータをデータフレームに変換
df_zn = pd.DataFrame(gdf.iloc[:,:-1].values, columns = list(gdf.columns.values)[:-1] )


print(datetime.datetime.now().time(),'鉄道LOS作成')
df_los_rail = los_rail.calc_los_rail(indir, outdir, src_proj, dst_proj, df_zn)


print(datetime.datetime.now().time(),'バスLOS作成')
df_los_bus = los_bus.calc_los_bus(indir, outdir, src_proj, dst_proj, df_zn)


print(datetime.datetime.now().time(),'自動車LOS作成')
df_los_car = los_car.calc_los_car(indir, outdir, src_proj, dst_proj, df_zn)

df_los = pd.concat([df_los_rail, df_los_bus, df_los_car], axis=1)
df_los.to_csv(path_ofile, encoding='Shift_Jis', index = False)

print(datetime.datetime.now().time(),'LOS作成終了')
os.system('PAUSE')
