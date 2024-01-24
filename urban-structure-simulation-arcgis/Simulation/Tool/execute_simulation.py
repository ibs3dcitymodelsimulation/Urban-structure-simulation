"""
都市構造シミュレーション機能
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

import arcpy


class SimulationException(Exception):
    pass


ROOT_DIR = os.path.abspath(Path(__file__).parents[2])
SIM_EXE_DIR = os.path.join(ROOT_DIR, "Simulation")
CONTROL_SIM = os.path.join(SIM_EXE_DIR, "Control_Sim.txt")
SIM_EXE = os.path.join(SIM_EXE_DIR, "Simulation.exe")
FACILITY_DATA_UPDATER = os.path.join(
    SIM_EXE_DIR, "DistZoneFacilityDataUpdater.exe"
)
LOG_PATH = os.path.join(SIM_EXE_DIR, "Tool", "Logs", "execute_simulation.log")


def run_exe(path: str) -> None:
    exe_name = os.path.basename(path)
    logger = set_log_format(f"run_exe: {exe_name}")
    logger.info("Start processing.")
    arcpy.AddMessage(f"{exe_name}実行中。")
    res = subprocess.run(
        path,
        cwd=os.path.dirname(SIM_EXE),
        capture_output=True,
    )

    # 実行が正常に終了しなかった場合エラー処理
    if res.returncode != 0:
        raise SimulationException(
            f"Error: {exe_name}が正常に終了しませんでした。", res.stderr
        )
    logger.info("Complete processing.")


def prepare_input(scenario_dir: str) -> str:
    """
    シミュレーション機能の前処理としてシナリオフォルダの入力を受け取り、シナリオのControl_Sim.txtとSimulation.exeの存在確認、
    シナリオのControl_Sim.txtの内容確認を行う
    """
    res = os.path.join(scenario_dir, "Control_Sim.txt")

    # シナリオのControl_Sim.txtの存在確認を行う
    if not res:
        raise SimulationException(
            "Error: シナリオフォルダにControl_Sim.txtが存在しないため終了します"
        )

    # 絶対パスを格納する
    return res


def run_exe_files() -> None:
    """
    都市構造シミュレーション実行ファイルを実行する
    """
    run_exe(FACILITY_DATA_UPDATER)
    run_exe(SIM_EXE)


def set_log_format(name: str, log_path: str = LOG_PATH) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.disabled = False
    logger.setLevel(logging.INFO)
    if len(logger.handlers) == 0:
        handler = logging.FileHandler(log_path)
        handler.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s [%(name)s] - %(levelname)s - %(message)s"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger


def create_control_sim(scenario_dir: str) -> None:
    # scenarioフォルダのControl_Sim.txtをsimulationフォルダにコピー(上書き保存)する
    shutil.copy(
        prepare_input(scenario_dir),
        CONTROL_SIM,
    )


def main(scenario_dir: str) -> None:
    """
    ユーザ入力としてシナリオのフォルダを入力され、シナリオフォルダ内ののControl_Sim.txtをSimulationフォルダ直下に上書き保存する
    Control_Sim.txtやSimulation.exeの確認とControl_Simファイル内に格納されている絶対パスの存在確認を行う
    都市構造シミュレーション機能の実行を行う。
    引数:
        なし
    返値:
        なし

    """

    logger = set_log_format("execute_simulation")
    logger.info("Start processing.")

    try:
        # Simulation.exeの存在確認をする
        if not (os.path.isfile(SIM_EXE)):
            raise SimulationException("Error: Simulation.exeが存在しないため終了します")
        create_control_sim(scenario_dir)
        run_exe_files()
        logger.info("Complete processing.")
    except SimulationException as e:
        logger.error(e, exc_info=True)
        arcpy.AddError(
            SimulationException("Error: 都市構造シミュレーション機能は正常に終了しませんでした", e)
        )


if __name__ == "__main__":
    main(arcpy.GetParameterAsText(0))
