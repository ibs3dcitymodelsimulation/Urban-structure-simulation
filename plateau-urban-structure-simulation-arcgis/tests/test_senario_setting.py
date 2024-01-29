from typing import Union

from Simulation.Tool.scenario_setting import (
    create_user_input_data,
    get_file_dict,
)


def test_get_file_dict():
    data: list[list[Union[int, str, None]]] = [
        [
            "A",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            2024,
            None,
            None,
            None,
            2020,
            None,
            None,
            None,
            2022,
            None,
            None,
            None,
            2023,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            2021,
            None,
        ]
    ]
    res = get_file_dict(
        create_user_input_data(data=data),
        root="C:\\path\\to",
    )
    exp = {
        "zone_data_path": "C:\\path\\to\\Simulation\\BaseData\\Zone.csv",
        "building_data_path": (
            "C:\\path\\to\\Simulation\\BaseData\\BaseData.gdb\\Building"
        ),
        "zone_traveltime_path": (
            "C:\\path\\to\\Simulation\\BaseData\\Zone_TravelTime.csv"
        ),
        "zone_facility_num_data_path": (
            "C:\\path\\to\\Simulation\\BaseData\\Zone_FacilityNum.csv"
        ),
        "output_directory_path": "C:\\path\\to\\Simulation\\Scenario\\A",
        "basedata_path": "C:\\path\\to\\Simulation\\BaseData",
        "sim_output_path": "C:\\path\\to\\Output\\A",
        "control_siminput_data_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Control_SimInput.csv"
        ),
        "control_simyear_data_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Control_SimYear.txt"
        ),
        "control_sim_data_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Control_Sim.txt"
        ),
        "dist_zone_facility_path": (
            "C:\\path\\to\\Simulation\\BaseData\\Dist_Zone_Facility.csv"
        ),
        "dist_building_station_path": (
            "C:\\path\\to\\Simulation\\BaseData\\Dist_Building_Station.csv"
        ),
        "land_price_change_rate_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Land_Price_Change_Rate.csv"
        ),
        "migration_rate_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Migration_Rate.csv"
        ),
        "output_zone_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Zone_2020.csv"
        ),
        "output_zone_traveltime_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Zone_TravelTime_2021.csv"
        ),
        "output_land_rate_path": (
            "C:\\path\\to\\Simulation\\"
            "Scenario\\A\\Land_Price_Change_Rate_2022.csv"
        ),
        "output_migration_rate_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Migration_Rate_2023.csv"
        ),
        "output_zone_facility_num_path": (
            "C:\\path\\to\\Simulation\\Scenario\\A\\Zone_FacilityNum_2024.csv"
        ),
        "control_sim_txt_path": "C:\\path\\to\\Simulation\\Control_Sim.txt",
    }
    assert res == exp
