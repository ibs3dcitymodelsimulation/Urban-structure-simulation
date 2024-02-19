from ipfn import ipfn
import pandas as pd
import warnings
import numpy as np
import random
from utilities.pooling import pooling
import bnlearn as bn
from utilities.get_marginal import get_marginal
# from utilities.custom_sample import custom_sample_with_dummy
from utilities.rounding import rounding
from utilities.custom_sample import custom_sample_with_dummy_multi

# ZonePopulationを生成
import PopulationZoneGeneration as pzg
pzg.calc_ZoneApportionment()

warnings.simplefilter(action='ignore', category=FutureWarning)
# hyperparameters
n_pools = 1
n_sampling = 1
np.random.seed(42)
bn_path = 'utilities/bnlearn_model_sendai.pkl'
bn_model = bn.load(filepath=bn_path)
population_nx = 10
# Read the control file to get the file path "fn"
with open('Control_Input.txt', 'r') as f:
    fn = f.readline().strip()
    output_location = f.readline().strip()

# load marginal data
pop_zone_df = pd.read_csv(f'{fn}/Population_Zone.csv', encoding='Shift-JIS')
pop_zone_df['gender'] = pop_zone_df['gender'] - 1
pop_zone_df['pop'] = population_nx * np.round(pop_zone_df['pop'], 0)
pop_zone_df = pop_zone_df.rename(
    columns={'gender': 'Seibetsu', 'pop': 'total'})

pop_gaf_df = pd.read_csv(f'{fn}/Population_GenderAgeFamily.csv', encoding='Shift-JIS')
pop_gaf_df['family'] = pop_gaf_df['family'] - 1
pop_gaf_df['gender'] = pop_gaf_df['gender'] - 1
pop_gaf_df['age'] = pop_gaf_df['age'] - 1
pop_gaf_df['pop'] = pop_gaf_df['pop'] * population_nx
pop_gaf_df = pop_gaf_df.rename(
    columns={'age': 'Nenrei_kaisou', 'gender': 'Seibetsu', 'pop': 'total', 'family': 'Kazoku_ruikei'})

population = int(round(pop_zone_df['total'].sum(), 0)) # * 10  # 十倍の人口を一気に生成

# pooling
pool_list = []
for i in range(n_pools):
    rounds = 1
    pool_df = pooling(model=bn_model, n_population=population, n_rounds=rounds)
    # ここでフィルタリング
    pool_list.append(pool_df)

zone_list = pop_zone_df['zone_code'].unique().tolist()

res_list = []

dimensions = [['Seibetsu', 'Kazoku_ruikei', 'Nenrei_kaisou'], ['zone_code', 'Seibetsu', 'age']]

full_cat_gender = [*range(2)]
full_cat_age = [*range(3)]
full_cat_family = [*range(5)]
full_cat_agegroup = [*range(18)]
for zone in zone_list:
    _data = pop_zone_df[pop_zone_df['zone_code'] == zone]
    for pool_df in pool_list:
        pool_df['total'] = 1
        if 'Unnamed: 0' in pool_df.columns:
            pool_df = pool_df.drop(columns=['Unnamed: 0'])
        # ランダム抽出を1回する。何回もすればより安定すると思う
        for j in range(n_sampling):
            # n must smaller than len(pool_df)
            df = pool_df.sample(n=max(int(_data['total'].sum()), 1))
            # !!複数のカテゴリーを対応できるように
            df = custom_sample_with_dummy_multi(df=df, full_df=pool_df, cat_list=['Seibetsu', 'age'])
            df['zone_code'] = zone
            res_list.append(df)

RES = pd.concat(res_list)
RES = custom_sample_with_dummy_multi(df=RES, full_df=pool_list[0],
                                     cat_list=['Seibetsu', 'Kazoku_ruikei', 'Nenrei_kaisou'])

print('population generation part one completed')

RES['total'] = RES['total'] / n_pools
RES = RES.reset_index(drop=True).reset_index()
RES = RES.rename(columns={'index': 'personal_id'})

idx_gender_family_agegroup = pd.MultiIndex.from_product([full_cat_gender, full_cat_family, full_cat_agegroup],
                                                        names=['Seibetsu', 'Kazoku_ruikei', 'Nenrei_kaisou'])
marginal1 = get_marginal(data=pop_gaf_df, marginal_names=[dimensions[0]])

idx_zone_gender_age = pd.MultiIndex.from_product([zone_list, full_cat_gender, full_cat_age],
                                                 names=['zone_code', 'Seibetsu', 'age'])
marginal2 = get_marginal(data=pop_zone_df,
                         marginal_names=[dimensions[1]], list_all_categories=[idx_zone_gender_age])

marginal = [marginal2[0], marginal1[0]]
dimensions = [dimensions[1], dimensions[0]]
# marginal = [marginal[0],marginal[2],marginal[1]]
# dimensions.append(['office_zone'])
# marginal = [i for i in marginal]
print('IPF BEGINS')
IPF = ipfn.ipfn(RES, marginal, dimensions)
RES = IPF.iteration()
print('IPF COMPLETED')
RES['total'] = RES['total']/population_nx
# print('rounding')
# RES = rounding(RES, col='total')
# dim = dimensions[1]
# pred = RES.groupby(dim)['total'].sum()
# truth = pop_gaf_df.groupby(dim)['total'].sum()
# q = pd.merge(pred, truth, on=dim)
# q.plot.scatter(x='total_x', y='total_y')
#
rename_dict = {'index': 'Personal_UniqueId',  # +=1?
               'zone': 'zone_code',
               'Seibetsu': 'Gender',  # +=1
               'Nenrei_kaisou': 'Age_Group',  # +=1
               'total': 'Expansion_Factor',
               'Haigu_kankei': 'Marital_Status',
               'Kazoku_ruikei': 'Family_Type',
               'Setainai_no_chii': 'Family_Position',
               # '': 'Marital_Status_Family_Position',
               # '': 'Minimum_Age_In_Household',
               'age': 'Age3',
               'Juukyokeitai': 'Juukyokeitai'}

RES = RES.rename(columns=rename_dict)
# RES['Marital_Status_Family_Position'] = RES['Marital_Status'].astype(str) + RES['Family_Position'].astype(str)
RES["Personal_UniqueId"] = range(1, len(RES) + 1)
# RES["zone_code"] = RES["zone"]
RES["Gender"] = RES["Gender"] + 1
RES["Age"] = -1
# RES["Expansion_Factor"] = RES["total"]
RES["Marital_Status"] = RES["Marital_Status"] + 1
RES["Family_Type"] = RES["Family_Type"] + 1
RES["Family_Position"] = RES["Family_Position"] + 1
RES["Marital_Status_Family_Position"] = RES["Marital_Status"] * 10 + RES["Family_Position"]
RES["Age_Group"] = RES["Age_Group"] + 1

# Ageを付与
# Age_Group に対応する年齢の範囲を定義する
age_group_mapping = {
    1: (0, 4),
    2: (5, 9),
    3: (10, 14),
    4: (15, 19),
    5: (20, 24),
    6: (25, 29),
    7: (30, 34),
    8: (35, 39),
    9: (40, 44),
    10: (45, 49),
    11: (50, 54),
    12: (55, 59),
    13: (60, 64),
    14: (65, 69),
    15: (70, 74),
    16: (75, 79),
    17: (80, 84),
    18: (85, 120)}  # 上限をどうするかは任意


def assign_random_age(row):
    age_range = age_group_mapping.get(row['Age_Group'])
    if age_range is None:
        return None  # Age_Groupが定義されていない場合はNoneを返す
    return random.randint(age_range[0], age_range[1])


RES['Age'] = RES.apply(assign_random_age, axis=1)

# 特定の Gender に対して、社人研仮定値に含まれる Marital_Status_Family_Position は決まっている。
# 許可されないレコードに対しては、許可される Marital_Status_Family_Position をランダムに割り当てる。
# この割り当ては、Expansion_Factor の構成比に基づく。
#
# Gender ごとにどの Marital_Status_Family_Position が許可されているか
allowed_positions = {
    1: [11, 15, 17, 21, 22, 23, 25, 27, 31, 34, 35, 37],
    2: [11, 15, 17, 21, 24, 26, 27, 31, 34, 35, 37]
}

# 主な処理
for age, positions in allowed_positions.items():
    # 許可されているレコードと許可されていないレコードを分ける
    mask_allowed = (RES['Gender'] == age) & RES['Marital_Status_Family_Position'].isin(positions)
    mask_not_allowed = (RES['Gender'] == age) & ~RES['Marital_Status_Family_Position'].isin(positions)

    # 許可されているレコードの Expansion_Factor の構成比を計算する
    total_expansion = RES.loc[mask_allowed, 'Expansion_Factor'].sum()
    probabilities = RES.loc[mask_allowed, 'Expansion_Factor'] / total_expansion

    # 許可されていないレコードに対してランダムに許可されている Marital_Status_Family_Position を割り当てる
    n = mask_not_allowed.sum()
    if n > 0:
        new_positions = np.random.choice(RES.loc[mask_allowed, 'Marital_Status_Family_Position'], size=n,
                                         p=probabilities)
        RES.loc[mask_not_allowed, 'Marital_Status_Family_Position'] = new_positions

RES = RES[["Personal_UniqueId",
           "zone_code",
           "Gender",
           "Age",
           "Expansion_Factor",
           "Marital_Status",
           "Family_Type",
           "Family_Position",
           "Marital_Status_Family_Position",
           "Age_Group"]]



# pop_zone_df = pd.read_csv(f'{fn}/Population_Zone.csv', encoding='Shift-JIS')
# pop_gaf_df = pd.read_csv(f'{fn}/Population_GenderAgeFamily.csv', encoding='Shift-JIS')
# left_dim = ['Family_Type']
# right_dim = ['family']
# pred_office = RES.groupby(left_dim)['Expansion_Factor'].sum()
# truth_office = pop_gaf_df.groupby(right_dim)['pop'].sum()
# p = pd.merge(pred_office, truth_office, left_on=left_dim, right_on=right_dim)
# p.plot.scatter(x='Expansion_Factor', y='pop')
print('rounding')
RES = rounding(RES, col='Expansion_Factor')

# 'personal_uniqueid'列をインデックスに設定
RES.set_index('Personal_UniqueId', inplace=True)

# インデックスを番号で振り直す
RES.reset_index(drop=True, inplace=True)

# 'Personal_UniqueId'列を追加
RES.insert(0, 'Personal_UniqueId', RES.index)
RES['Personal_UniqueId'] = RES['Personal_UniqueId'] + 1

RES.to_csv(f'{output_location}/individual.csv', index=False, encoding='Shift-JIS')